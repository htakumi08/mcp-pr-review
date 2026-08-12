from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Generic, TypeVar
from urllib.parse import quote

import httpx

from backlog_mcp.backlog.dto import Comment, Issue, parse_comments, parse_issue
from backlog_mcp.backlog.errors import (
    BacklogForbiddenError,
    BacklogNotFoundError,
    BacklogRateLimitedError,
    BacklogSchemaError,
    BacklogTimeoutError,
    BacklogTransportError,
    BacklogUnauthorizedError,
)
from backlog_mcp.config import Settings

ISSUE_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*-[1-9][0-9]*$")
T = TypeVar("T")


@dataclass(frozen=True)
class Page(Generic[T]):
    items: tuple[T, ...]
    truncated: bool


class BacklogClient:
    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._client = http_client or httpx.AsyncClient(
            timeout=settings.timeout_seconds,
            follow_redirects=False,
        )

    async def __aenter__(self) -> BacklogClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_issue(self, issue_id_or_key: str | int) -> Issue:
        normalized_key = validate_issue_identifier(issue_id_or_key)
        payload = await self._get_json(
            f"/api/v2/issues/{quote(normalized_key, safe='')}",
            params={},
        )
        return parse_issue(payload)

    async def get_comments(self, issue_key: str, max_items: int) -> Page[Comment]:
        normalized_key = validate_issue_key(issue_key)
        comments: list[Comment] = []
        while len(comments) <= max_items:
            count = min(100, max_items + 1 - len(comments))
            params = {"count": str(count), "order": "asc"}
            if comments:
                params["minId"] = str(comments[-1].id + 1)
            payload = await self._get_json(
                f"/api/v2/issues/{quote(normalized_key, safe='')}/comments",
                params=params,
            )
            page = parse_comments(payload)
            comments.extend(page)
            if len(page) < count:
                break
        return Page(tuple(comments[:max_items]), len(comments) > max_items)

    async def get_child_issues(
        self, parent_issue_id: int, max_items: int
    ) -> Page[Issue]:
        payload = await self._get_json(
            "/api/v2/issues",
            params={
                "parentIssueId[]": str(parent_issue_id),
                "count": str(min(max_items + 1, 100)),
                "order": "asc",
                "sort": "created",
            },
        )
        issues = [parse_issue(item) for item in _payload_list(payload, "issues")]
        return Page(tuple(issues[:max_items]), len(issues) > max_items)

    async def get_related_issues(
        self, issue_key: str, max_items: int
    ) -> Page[Issue]:
        normalized_key = validate_issue_key(issue_key)
        payload = await self._get_json(
            f"/api/v2/issues/{quote(normalized_key, safe='')}/relatedIssues",
            params={},
        )
        issues = [parse_issue(item) for item in _payload_list(payload, "related issues")]
        return Page(tuple(issues[:max_items]), len(issues) > max_items)

    async def _get_json(
        self,
        path: str,
        params: dict[str, str],
    ) -> Any:
        request_params = {**params, "apiKey": self._settings.api_key}
        try:
            response = await self._client.get(
                f"{self._settings.base_url}{path}",
                params=request_params,
                follow_redirects=False,
            )
        except httpx.TimeoutException:
            raise BacklogTimeoutError("Backlog API request timed out") from None
        except httpx.RequestError:
            raise BacklogTransportError("Backlog API request failed") from None

        if response.status_code == 401:
            raise BacklogUnauthorizedError("Backlog API authentication failed")
        if response.status_code == 403:
            raise BacklogForbiddenError("Backlog API access was forbidden")
        if response.status_code == 404:
            raise BacklogNotFoundError("Backlog issue was not found")
        if response.status_code == 429:
            raise BacklogRateLimitedError(response.headers.get("X-RateLimit-Reset"))
        if not 200 <= response.status_code < 300:
            raise BacklogTransportError(
                f"Backlog API returned HTTP {response.status_code}"
            )

        try:
            return response.json()
        except ValueError:
            raise BacklogSchemaError("Backlog API returned invalid JSON") from None


def validate_issue_key(issue_key: str) -> str:
    normalized_key = issue_key.strip().upper()
    if not ISSUE_KEY_PATTERN.fullmatch(normalized_key):
        raise ValueError("invalid Backlog issue key")
    return normalized_key


def validate_issue_identifier(issue_id_or_key: str | int) -> str:
    if isinstance(issue_id_or_key, int) and not isinstance(issue_id_or_key, bool):
        if issue_id_or_key < 1:
            raise ValueError("invalid Backlog issue identifier")
        return str(issue_id_or_key)
    if isinstance(issue_id_or_key, str):
        return validate_issue_key(issue_id_or_key)
    raise ValueError("invalid Backlog issue identifier")


def _payload_list(payload: object, name: str) -> list[Any]:
    if not isinstance(payload, list):
        raise BacklogSchemaError(f"Backlog API returned an invalid {name} list")
    return payload
