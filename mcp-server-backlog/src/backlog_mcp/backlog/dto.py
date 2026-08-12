from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backlog_mcp.backlog.errors import BacklogSchemaError


@dataclass(frozen=True)
class User:
    id: int
    name: str


@dataclass(frozen=True)
class ChangeLog:
    field: str
    new_value: str | None
    original_value: str | None


@dataclass(frozen=True)
class Comment:
    id: int
    content: str
    created_user: User
    created_at: str
    updated_at: str
    change_logs: tuple[ChangeLog, ...]


@dataclass(frozen=True)
class Issue:
    id: int
    key: str
    project_id: int
    summary: str
    description: str
    status: str
    priority: str
    issue_type: str
    assignee: User | None
    parent_issue_id: int | None
    custom_fields: tuple[dict[str, Any], ...]
    categories: tuple[str, ...]
    versions: tuple[str, ...]
    milestones: tuple[str, ...]
    created_at: str
    updated_at: str


def parse_issue(payload: object) -> Issue:
    data = _mapping(payload, "issue")
    status = _mapping(data.get("status"), "issue.status")
    priority = _mapping(data.get("priority"), "issue.priority")
    issue_type = _mapping(data.get("issueType"), "issue.issueType")
    assignee_data = data.get("assignee")

    return Issue(
        id=_integer(data, "id", "issue"),
        key=_string(data, "issueKey", "issue"),
        project_id=_integer(data, "projectId", "issue"),
        summary=_string(data, "summary", "issue"),
        description=_nullable_string(data.get("description")) or "",
        status=_string(status, "name", "issue.status"),
        priority=_string(priority, "name", "issue.priority"),
        issue_type=_string(issue_type, "name", "issue.issueType"),
        assignee=parse_user(assignee_data) if assignee_data is not None else None,
        parent_issue_id=_nullable_integer(data.get("parentIssueId"), "parentIssueId"),
        custom_fields=tuple(_mapping(item, "custom field") for item in _list(data.get("customFields", []), "customFields")),
        categories=_names(data.get("category", []), "category"),
        versions=_names(data.get("versions", []), "versions"),
        milestones=_names(data.get("milestone", []), "milestone"),
        created_at=_string(data, "created", "issue"),
        updated_at=_string(data, "updated", "issue"),
    )


def parse_comments(payload: object) -> list[Comment]:
    return [parse_comment(item) for item in _list(payload, "comments")]


def parse_comment(payload: object) -> Comment:
    data = _mapping(payload, "comment")
    change_log_data = data.get("changeLog")
    change_logs = (
        ()
        if change_log_data is None
        else tuple(parse_change_log(item) for item in _list(change_log_data, "changeLog"))
    )
    return Comment(
        id=_integer(data, "id", "comment"),
        content=_nullable_string(data.get("content")) or "",
        created_user=parse_user(data.get("createdUser")),
        created_at=_string(data, "created", "comment"),
        updated_at=_string(data, "updated", "comment"),
        change_logs=change_logs,
    )


def parse_change_log(payload: object) -> ChangeLog:
    data = _mapping(payload, "changeLog item")
    return ChangeLog(
        field=_string(data, "field", "changeLog item"),
        new_value=_nullable_string(data.get("newValue")),
        original_value=_nullable_string(data.get("originalValue")),
    )


def parse_user(payload: object) -> User:
    data = _mapping(payload, "user")
    return User(
        id=_integer(data, "id", "user"),
        name=_string(data, "name", "user"),
    )


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BacklogSchemaError(f"Backlog API returned an invalid {name} object")
    return value


def _list(value: object, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise BacklogSchemaError(f"Backlog API returned an invalid {name} list")
    return value


def _string(data: dict[str, Any], key: str, name: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise BacklogSchemaError(f"Backlog API returned an invalid {name}.{key}")
    return value


def _integer(data: dict[str, Any], key: str, name: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise BacklogSchemaError(f"Backlog API returned an invalid {name}.{key}")
    return value


def _nullable_string(value: object) -> str | None:
    if value is None or isinstance(value, str):
        return value
    raise BacklogSchemaError("Backlog API returned a value that is not a string or null")


def _nullable_integer(value: object, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise BacklogSchemaError(f"Backlog API returned an invalid {name}")


def _names(value: object, name: str) -> tuple[str, ...]:
    return tuple(
        _string(_mapping(item, f"{name} item"), "name", f"{name} item")
        for item in _list(value, name)
    )
