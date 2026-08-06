"""Validate engineering reasoning results."""

from __future__ import annotations

from confidence_engine import ConfidenceEngine
from reasoning_exceptions import ReasoningValidationError
from reasoning_models import EngineeringReasoningResult


class ReasoningValidator:
    """Validate typed engineering reasoning output."""

    @staticmethod
    def validate(result: EngineeringReasoningResult) -> None:
        if not result.reasoning_id:
            raise ReasoningValidationError("reasoning_id is required.")
        if not result.task_type:
            raise ReasoningValidationError("task_type is required.")
        if not result.summary.strip():
            raise ReasoningValidationError("summary must not be empty.")
        if not result.checksum:
            raise ReasoningValidationError("checksum is required.")
        if not result.generated_timestamp:
            raise ReasoningValidationError("generated_timestamp is required.")

        ConfidenceEngine.validate(result.confidence)

        if result.recommendations is None:
            raise ReasoningValidationError("recommendations must be present.")
        if result.warnings is None:
            raise ReasoningValidationError("warnings must be present.")
        if result.observations is None:
            raise ReasoningValidationError("observations must be present.")
        if result.assumptions is None:
            raise ReasoningValidationError("assumptions must be present.")
        if not isinstance(result.metadata, dict):
            raise ReasoningValidationError("metadata must be a dictionary.")
