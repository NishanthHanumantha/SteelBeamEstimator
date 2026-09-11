"""Typed structured response models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class JSONEngineError(Exception):
    """Base error for JSON response engine failures."""


class JSONExtractionError(JSONEngineError):
    """Raised when JSON cannot be extracted from Claude text."""


class SchemaValidationError(JSONEngineError):
    """Raised when JSON fails schema validation."""


class ResponseBuildError(JSONEngineError):
    """Raised when validated JSON cannot be converted to a typed model."""


class ResponseRetryError(JSONEngineError):
    """Raised when all retry attempts are exhausted."""


class ConfidenceValidationError(SchemaValidationError):
    """Raised when confidence field is missing or out of range."""


@dataclass
class StructuredResponse:
    """Validated structured response returned to engineering modules."""

    schema_name: str
    schema_version: str
    raw_json: Dict[str, Any]
    validated_data: Dict[str, Any]
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    model_type: str = "StructuredResponse"

    @staticmethod
    def timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()


@dataclass
class BeamReasoningResponse(StructuredResponse):
    model_type: str = "BeamReasoningResponse"


@dataclass
class ReinforcementParserResponse(StructuredResponse):
    model_type: str = "ReinforcementParserResponse"


@dataclass
class AnnotationInterpreterResponse(StructuredResponse):
    model_type: str = "AnnotationInterpreterResponse"


@dataclass
class QAValidatorResponse(StructuredResponse):
    model_type: str = "QAValidatorResponse"


SCHEMA_MODEL_MAP = {
    "BEAM_REASONING": BeamReasoningResponse,
    "REINFORCEMENT_PARSER": ReinforcementParserResponse,
    "ANNOTATION_INTERPRETER": AnnotationInterpreterResponse,
    "QA_VALIDATOR": QAValidatorResponse,
    "SAMPLE_RESPONSE": StructuredResponse,
    "BASE_RESPONSE": StructuredResponse,
    "CONFIDENCE": StructuredResponse,
}
