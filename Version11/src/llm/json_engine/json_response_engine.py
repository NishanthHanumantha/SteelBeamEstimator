"""Structured JSON response orchestrator."""

from __future__ import annotations

import time
from typing import Any, Dict

from loguru import logger

from src.llm.json_engine.json_extractor import JSONExtractor
from src.llm.json_engine.response_builder import ResponseBuilder
from src.llm.json_engine.response_models import JSONEngineError, StructuredResponse
from src.llm.json_engine.schema_registry import SchemaRegistry
from src.llm.json_engine.schema_validator import SchemaValidator


class JSONResponseEngine:
    """Extract, validate, and type Claude JSON responses."""

    def __init__(
        self,
        registry: SchemaRegistry | None = None,
        extractor: JSONExtractor | None = None,
        validator: SchemaValidator | None = None,
        builder: ResponseBuilder | None = None,
    ) -> None:
        self._registry = registry or SchemaRegistry()
        self._extractor = extractor or JSONExtractor()
        self._validator = validator or SchemaValidator(self._registry)
        self._builder = builder or ResponseBuilder()

    def parse_response(self, response_text: str, schema_name: str) -> StructuredResponse:
        started = time.perf_counter()
        loaded_schema = self._registry.get_schema(schema_name)

        extract_started = time.perf_counter()
        payload = self._extractor.extract(response_text)
        extract_duration = time.perf_counter() - extract_started
        if not isinstance(payload, dict):
            raise JSONEngineError("Structured responses must be JSON objects.")

        validate_started = time.perf_counter()
        self._validator.validate(payload, schema_name)
        validate_duration = time.perf_counter() - validate_started

        structured = self._builder.build(payload, loaded_schema)
        structured.metadata.update(
            {
                "extraction_duration_s": round(extract_duration, 4),
                "validation_duration_s": round(validate_duration, 4),
                "response_size": len(response_text),
                "validation_result": "PASS",
            }
        )

        logger.info(
            "JSON response parsed schema={} schema_version={} validation_result=PASS "
            "confidence={} response_size={} extraction_duration_s={:.4f} "
            "validation_duration_s={:.4f}",
            structured.schema_name,
            structured.schema_version,
            structured.confidence,
            len(response_text),
            extract_duration,
            validate_duration,
        )
        _ = time.perf_counter() - started
        return structured
