"""Custom exceptions for the centralized Claude provider layer."""

from __future__ import annotations


class ClaudeAPIError(Exception):
    """Base error for Claude API failures."""


class ClaudeAuthenticationError(ClaudeAPIError):
    """Raised when .env loading or API key validation fails."""


class ClaudeRateLimitError(ClaudeAPIError):
    """Raised when Anthropic rate limits are exceeded."""

    def __init__(self, message: str = "", *, retry_after_s: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_s = retry_after_s


class ClaudeTimeoutError(ClaudeAPIError):
    """Raised when a Claude request exceeds the configured timeout."""


class ClaudeResponseFormatError(ClaudeAPIError):
    """Raised when the Claude response cannot be parsed into plain text."""
