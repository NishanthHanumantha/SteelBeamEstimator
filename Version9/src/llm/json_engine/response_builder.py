"""Build typed structured response models."""

from __future__ import annotations

from typing import Any, Dict

from src.llm.json_engine.response_models import (
    SCHEMA_MODEL_MAP,
    ResponseBuildError,
    StructuredResponse,
)
from src.llm.json_engine.schema_registry import LoadedSchema


class ResponseBuilder:
    """Convert validated JSON into strongly typed response models."""

    def build(self, payload: Dict[str, Any], loaded_schema: LoadedSchema) -> StructuredResponse:
        try:
            model_cls = SCHEMA_MODEL_MAP.get(loaded_schema.schema_name, StructuredResponse)
            confidence = float(payload["confidence"])
            return model_cls(
                schema_name=loaded_schema.schema_name,
                schema_version=loaded_schema.schema_version,
                raw_json=dict(payload),
                validated_data=dict(payload),
                confidence=confidence,
                metadata={
                    "schema_path": loaded_schema.schema_path,
                    "model_type": model_cls.__name__,
                },
            )
        except Exception as exc:
            raise ResponseBuildError(f"Failed to build typed response: {exc}") from exc
