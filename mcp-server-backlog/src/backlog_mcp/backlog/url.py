from __future__ import annotations

from urllib.parse import urlsplit

from backlog_mcp.backlog.client import validate_issue_key


class BacklogUrlError(ValueError):
    """Raised when a URL does not identify an issue in the configured space."""


def extract_issue_key(backlog_url: str, base_url: str) -> str:
    try:
        target = urlsplit(backlog_url.strip())
        allowed = urlsplit(base_url)
        target_port = target.port
        allowed_port = allowed.port
    except ValueError as exc:
        raise BacklogUrlError("invalid Backlog issue URL") from exc

    target_origin = (target.scheme, target.hostname, target_port or 443)
    allowed_origin = (allowed.scheme, allowed.hostname, allowed_port or 443)
    if (
        target_origin != allowed_origin
        or target.username is not None
        or target.password is not None
    ):
        raise BacklogUrlError("Backlog issue URL is outside the configured space")

    path_parts = target.path.rstrip("/").split("/")
    if len(path_parts) != 3 or path_parts[0] != "" or path_parts[1] != "view":
        raise BacklogUrlError("Backlog issue URL must use /view/<issue-key>")
    try:
        return validate_issue_key(path_parts[2])
    except ValueError as exc:
        raise BacklogUrlError("Backlog issue URL contains an invalid issue key") from exc
