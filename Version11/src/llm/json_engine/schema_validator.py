"""Validate JSON payloads against registered schemas."""

from __future__ import annotations

from typing import Any, Dict, List

from jsonschema import ValidationError

from src.llm.json_engine.response_models import ConfidenceValidationError, SchemaValidationError
from src.llm.json_engine.schema_registry import SchemaRegistry


class SchemaValidator:
    """Validate JSON documents against schema registry entries."""

    def __init__(self, registry: SchemaRegistry | None = None) -> None:
        self._registry = registry or SchemaRegistry()

    def validate(self, payload: Dict[str, Any], schema_name: str) -> None:
        self._validate_confidence(payload, schema_name)
        validator = self._registry.get_validator(schema_name)
        errors: List[str] = []
        for error in sorted(validator.iter_errors(payload), key=lambda item: str(item.path)):
            errors.append(self._format_error(error))
        if errors:
            raise SchemaValidationError(
                f"Schema validation failed for {schema_name}: " + "; ".join(errors)
            )

    @staticmethod
    def _validate_confidence(payload: Dict[str, Any], schema_name: str) -> None:
        if "confidence" not in payload:
            raise ConfidenceValidationError(
                f"Schema {schema_name} requires confidence between 0.0 and 1.0."
            )
        confidence = payload["confidence"]
        if not isinstance(confidence, (int, float)):
            raise ConfidenceValidationError("Confidence must be numeric.")
        if confidence < 0.0:
            raise ConfidenceValidationError("Confidence cannot be negative.")
        if confidence > 1.0:
            raise ConfidenceValidationError("Confidence cannot exceed 1.0.")

    @staticmethod
    def _format_error(error: ValidationError) -> str:
        path = ".".join(str(part) for part in error.path) or "root"
        return f"{path}: {error.message}"
