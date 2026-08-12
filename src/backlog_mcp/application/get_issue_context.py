from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol, Self

from backlog_mcp.backlog.client import Page
from backlog_mcp.backlog.dto import Comment, Issue
from backlog_mcp.backlog.errors import BacklogError
from backlog_mcp.backlog.url import extract_issue_key
from backlog_mcp.config import Settings


@dataclass(frozen=True)
class _CacheEntry:
    expires_at: float
    value: dict[str, Any]


class IssueContextClient(Protocol):
    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, *args: object) -> None: ...

    async def get_issue(self, issue_id_or_key: str | int) -> Issue: ...

    async def get_comments(self, issue_key: str, max_items: int) -> Page[Comment]: ...

    async def get_child_issues(
        self, parent_issue_id: int, max_items: int
    ) -> Page[Issue]: ...

    async def get_related_issues(
        self, issue_key: str, max_items: int
    ) -> Page[Issue]: ...


class GetIssueContext:
    def __init__(
        self,
        settings: Settings,
        client_factory: Callable[[], IssueContextClient],
    ) -> None:
        self._settings = settings
        self._client_factory = client_factory
        self._cache: dict[str, _CacheEntry] = {}

    async def execute(self, backlog_url: str) -> dict[str, Any]:
        issue_key = extract_issue_key(backlog_url, self._settings.base_url)
        cached = self._cache.get(issue_key)
        now = time.monotonic()
        if cached is not None and cached.expires_at > now:
            return cached.value

        warnings: list[dict[str, str]] = []
        async with self._client_factory() as client:
            issue = await client.get_issue(issue_key)
            comments = await self._optional(
                "comments",
                lambda: client.get_comments(issue_key, self._settings.max_comments),
                warnings,
            )
            parent = None
            if issue.parent_issue_id is not None:
                parent = await self._optional(
                    "parent_issue",
                    lambda: client.get_issue(issue.parent_issue_id),
                    warnings,
                )
            children = await self._optional(
                "child_issues",
                lambda: client.get_child_issues(
                    issue.id, self._settings.max_related_issues
                ),
                warnings,
            )
            related = await self._optional(
                "related_issues",
                lambda: client.get_related_issues(
                    issue.key, self._settings.max_related_issues
                ),
                warnings,
            )

        comment_page = comments if isinstance(comments, Page) else Page((), False)
        child_page = children if isinstance(children, Page) else Page((), False)
        related_page = related if isinstance(related, Page) else Page((), False)
        result = {
            "issue": _issue_dict(issue, include_description=True),
            "comments": [_comment_dict(comment) for comment in comment_page.items],
            "change_logs": [
                {
                    "comment_id": comment.id,
                    "changed_at": comment.created_at,
                    "changed_by": _user_dict(comment.created_user),
                    "field": change.field,
                    "original_value": change.original_value,
                    "new_value": change.new_value,
                }
                for comment in comment_page.items
                for change in comment.change_logs
            ],
            "relationships": {
                "parent": _issue_dict(parent) if isinstance(parent, Issue) else None,
                "children": [_issue_dict(item) for item in child_page.items],
                "related": [_issue_dict(item) for item in related_page.items],
            },
            "retrieval": {
                "source_url": f"{self._settings.base_url}/view/{issue.key}",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "comment_count": len(comment_page.items),
                "comments_truncated": comment_page.truncated,
                "children_truncated": child_page.truncated,
                "related_issues_truncated": related_page.truncated,
                "partial": bool(warnings)
                or comment_page.truncated
                or child_page.truncated
                or related_page.truncated,
                "warnings": warnings,
            },
        }
        self._cache[issue_key] = _CacheEntry(
            expires_at=now + self._settings.cache_ttl_seconds,
            value=result,
        )
        return result

    async def _optional(
        self,
        source: str,
        operation: Callable[[], Awaitable[Any]],
        warnings: list[dict[str, str]],
    ) -> Any:
        try:
            return await operation()
        except BacklogError as exc:
            warnings.append({"source": source, "error": type(exc).__name__})
            return None


def _user_dict(user: Any) -> dict[str, Any]:
    return {"id": user.id, "name": user.name}


def _issue_dict(issue: Issue, *, include_description: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": issue.id,
        "key": issue.key,
        "project_id": issue.project_id,
        "summary": issue.summary,
        "status": issue.status,
        "priority": issue.priority,
        "issue_type": issue.issue_type,
        "assignee": _user_dict(issue.assignee) if issue.assignee else None,
        "parent_issue_id": issue.parent_issue_id,
        "created_at": issue.created_at,
        "updated_at": issue.updated_at,
    }
    if include_description:
        result.update(
            description=issue.description,
            custom_fields=list(issue.custom_fields),
            categories=list(issue.categories),
            versions=list(issue.versions),
            milestones=list(issue.milestones),
        )
    return result


def _comment_dict(comment: Comment) -> dict[str, Any]:
    return {
        "id": comment.id,
        "content": comment.content,
        "created_user": _user_dict(comment.created_user),
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
    }
