from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlsplit


class ConfigurationError(ValueError):
    """Raised when required server configuration is invalid."""


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str = field(repr=False)
    timeout_seconds: float = 10.0
    max_comments: int = 500
    max_related_issues: int = 20
    cache_ttl_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> Settings:
        return cls.from_mapping(os.environ)

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]) -> Settings:
        base_url = normalize_base_url(values.get("BACKLOG_BASE_URL", ""))
        api_key = values.get("BACKLOG_API_KEY", "").strip()
        if not api_key:
            raise ConfigurationError("BACKLOG_API_KEY is required")

        timeout_raw = values.get("BACKLOG_TIMEOUT_SECONDS", "10").strip()
        try:
            timeout_seconds = float(timeout_raw)
        except ValueError as exc:
            raise ConfigurationError("BACKLOG_TIMEOUT_SECONDS must be a number") from exc
        if not 0.1 <= timeout_seconds <= 60:
            raise ConfigurationError(
                "BACKLOG_TIMEOUT_SECONDS must be between 0.1 and 60"
            )

        max_comments = _bounded_integer(
            values, "BACKLOG_MAX_COMMENTS", default=500, minimum=1, maximum=5000
        )
        max_related_issues = _bounded_integer(
            values, "BACKLOG_MAX_RELATED_ISSUES", default=20, minimum=1, maximum=100
        )
        cache_ttl_seconds = _bounded_float(
            values, "BACKLOG_CACHE_TTL_SECONDS", default=60.0, minimum=0, maximum=3600
        )

        return cls(
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            max_comments=max_comments,
            max_related_issues=max_related_issues,
            cache_ttl_seconds=cache_ttl_seconds,
        )


def normalize_base_url(value: str) -> str:
    base_url = value.strip().rstrip("/")
    try:
        parsed = urlsplit(base_url)
        port = parsed.port
    except ValueError as exc:
        raise ConfigurationError("BACKLOG_BASE_URL is invalid") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or (port is not None and port != 443)
    ):
        raise ConfigurationError(
            "BACKLOG_BASE_URL must be an HTTPS origin without credentials, path, query, or fragment"
        )
    return base_url


def _bounded_integer(
    values: Mapping[str, str],
    name: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = values.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum} and {maximum}")
    return value


def _bounded_float(
    values: Mapping[str, str],
    name: str,
    *,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    raw = values.get(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number") from exc
    if not minimum <= value <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum} and {maximum}")
    return value
