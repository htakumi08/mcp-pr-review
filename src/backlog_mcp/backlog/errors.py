from __future__ import annotations


class BacklogError(Exception):
    """Base error for sanitized Backlog API failures."""


class BacklogUnauthorizedError(BacklogError):
    pass


class BacklogForbiddenError(BacklogError):
    pass


class BacklogNotFoundError(BacklogError):
    pass


class BacklogRateLimitedError(BacklogError):
    def __init__(self, reset_at: str | None) -> None:
        super().__init__("Backlog API rate limit exceeded")
        self.reset_at = reset_at


class BacklogTimeoutError(BacklogError):
    pass


class BacklogTransportError(BacklogError):
    pass


class BacklogSchemaError(BacklogError):
    pass

