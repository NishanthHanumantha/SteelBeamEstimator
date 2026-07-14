"""Exceptions for the Engineering Reasoning Engine."""


class ReasoningError(Exception):
    """Base error for engineering reasoning failures."""


class ReasoningValidationError(ReasoningError):
    """Raised when reasoning output fails validation."""


class UnsupportedReasoningTaskError(ReasoningError):
    """Raised when a reasoning task is not registered."""


class ReasoningCacheError(ReasoningError):
    """Raised when reasoning cache operations fail."""


class ReasoningOutputError(ReasoningError):
    """Raised when reasoning outputs cannot be persisted."""
