from __future__ import annotations

from typing import Any, Optional


class BrokerError(Exception):
    """Base error for brokers2."""

    def __init__(self, message: str, *, context: Optional[dict[str, Any]] = None) -> None:  # noqa: D401
        super().__init__(message)
        self.context = context or {}


class AuthError(BrokerError):
    """Authentication or authorization failed."""


class RateLimitError(BrokerError):
    """Rate limits exceeded."""


class TimeoutError(BrokerError):
    """Network or broker timeout."""


class UnsupportedOperationError(BrokerError):
    """Called a method that the broker capability does not support."""


class MarginUnavailableError(BrokerError):
    """Margin must be fetched from broker and is unavailable or failed."""


class ValidationError(BrokerError):
    """Input validation failed."""


class HTTPError(BrokerError):
    """HTTP call failed."""


