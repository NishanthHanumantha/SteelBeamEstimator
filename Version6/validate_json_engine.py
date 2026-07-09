"""Phase LLM.2 — Structured JSON Response Engine validation."""

from __future__ import annotations

import sys
import time
from typing import Any
from unittest import mock

from src.llm.json_engine.json_extractor import JSONExtractor
from src.llm.json_engine.json_response_engine import JSONResponseEngine
from src.llm.json_engine.response_builder import ResponseBuilder
from src.llm.json_engine.response_models import (
    ConfidenceValidationError,
    JSONExtractionError,
    SchemaValidationError,
)
from src.llm.json_engine.response_retry import ResponseRetryEngine, RETRY_SUFFIX
from src.llm.json_engine.schema_registry import MODEL_VERSION, PHASE, SCHEMA_REGISTRY, SchemaRegistry
from src.llm.json_engine.schema_validator import SchemaValidator
from src.llm.prompt_executor import PromptExecutor


def _check(name: str, passed: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def validate_schema_loading() -> list[dict[str, Any]]:
    registry = SchemaRegistry()
    checks = [_check("Schema registry populated", len(SCHEMA_REGISTRY) >= 7)]
    for name in SCHEMA_REGISTRY:
        loaded = registry.get_schema(name)
        checks.append(_check(f"Schema loads {name}", bool(loaded.schema_document)))
        checks.append(_check(f"Schema path valid {name}", loaded.schema_path.endswith(".schema.json")))
    return checks


def validate_schema_caching() -> list[dict[str, Any]]:
    registry = SchemaRegistry()
    first = registry.get_schema("SAMPLE_RESPONSE")
    second = registry.get_schema("SAMPLE_RESPONSE")
    validator_first = registry.get_validator("SAMPLE_RESPONSE")
    validator_second = registry.get_validator("SAMPLE_RESPONSE")
    return [
        _check("Schema cache key stable", first.cache_key == second.cache_key),
        _check("Compiled validator cached", validator_first is validator_second),
    ]


def validate_json_extraction() -> list[dict[str, Any]]:
    extractor = JSONExtractor()
    pure = extractor.extract('{"result":"ok","confidence":0.9}')
    markdown = extractor.extract(
        'Here is the result:\n```json\n{"result":"ok","confidence":0.85}\n```\nThanks.'
    )
    mixed = extractor.extract('Analysis complete {"result":"ok","confidence":0.75} end')
    checks = [
        _check("Pure JSON extraction", pure["result"] == "ok"),
        _check("Markdown JSON extraction", markdown["confidence"] == 0.85),
        _check("Mixed text JSON extraction", mixed["confidence"] == 0.75),
    ]
    try:
        extractor.extract("not json at all")
        checks.append(_check("Malformed JSON rejected", False))
    except JSONExtractionError:
        checks.append(_check("Malformed JSON rejected", True))
    return checks


def validate_schema_validation() -> list[dict[str, Any]]:
    validator = SchemaValidator()
    valid = {"result": "ok", "confidence": 0.9}
    checks = []
    validator.validate(valid, "SAMPLE_RESPONSE")
    checks.append(_check("Valid payload accepted", True))

    try:
        validator.validate({"result": "ok"}, "SAMPLE_RESPONSE")
        checks.append(_check("Missing confidence rejected", False))
    except ConfidenceValidationError:
        checks.append(_check("Missing confidence rejected", True))

    try:
        validator.validate({"result": "ok", "confidence": 1.5}, "SAMPLE_RESPONSE")
        checks.append(_check("Confidence > 1 rejected", False))
    except ConfidenceValidationError:
        checks.append(_check("Confidence > 1 rejected", True))

    try:
        validator.validate({"result": "ok", "confidence": -0.1}, "SAMPLE_RESPONSE")
        checks.append(_check("Negative confidence rejected", False))
    except ConfidenceValidationError:
        checks.append(_check("Negative confidence rejected", True))

    try:
        validator.validate({"result": 123, "confidence": 0.5}, "SAMPLE_RESPONSE")
        checks.append(_check("Wrong type rejected", False))
    except SchemaValidationError:
        checks.append(_check("Wrong type rejected", True))
    return checks


def validate_typed_model_creation() -> list[dict[str, Any]]:
    engine = JSONResponseEngine()
    structured = engine.parse_response(
        '{"result":"JSON Engine OK","confidence":0.95,"template_name":"SAMPLE_PROMPT"}',
        "SAMPLE_RESPONSE",
    )
    return [
        _check("Typed model created", isinstance(structured.validated_data, dict)),
        _check("StructuredResponse returned", structured.schema_name == "SAMPLE_RESPONSE"),
        _check("Confidence stored", structured.confidence == 0.95),
        _check("Metadata populated", bool(structured.metadata)),
    ]


def validate_retry_logic() -> list[dict[str, Any]]:
    calls: list[str | None] = []

    def fetch_response(correction: str | None) -> str:
        calls.append(correction)
        if len(calls) < 3:
            return "invalid json"
        return '{"result":"retry-ok","confidence":0.8}'

    result = ResponseRetryEngine().execute(fetch_response, "SAMPLE_RESPONSE")
    return [
        _check("Retry returns structured response", result.validated_data["result"] == "retry-ok"),
        _check("Retry attempts executed", len(calls) == 3),
        _check("Retry correction prompt used", calls[1] == RETRY_SUFFIX),
    ]


def validate_prompt_executor_integration() -> list[dict[str, Any]]:
    executor = PromptExecutor()
    valid_json = '{"result":"executor-ok","confidence":0.91,"template_name":"SAMPLE_PROMPT"}'

    with mock.patch.object(executor._client, "generate_response", return_value=valid_json):
        structured = executor.execute_json(
            "SAMPLE_PROMPT",
            "SAMPLE_RESPONSE",
            {"expected_response": "executor-ok", "template_name": "SAMPLE_PROMPT"},
        )
    checks = [
        _check("execute_json returns StructuredResponse", structured.validated_data["result"] == "executor-ok"),
    ]

    with mock.patch.object(executor._client, "generate_response", return_value="plain text"):
        legacy = executor.execute(user_prompt="plain text")
        checks.append(_check("execute() backward compatible", legacy == "plain text"))

    with mock.patch.object(executor._client, "generate_response", return_value="template text"):
        template_text = executor.execute_template(
            "SAMPLE_PROMPT",
            {"expected_response": "x", "template_name": "SAMPLE_PROMPT"},
        )
        checks.append(_check("execute_template() backward compatible", template_text == "template text"))
    return checks


def run_validation() -> dict[str, Any]:
    started = time.perf_counter()
    sections = [
        validate_schema_loading,
        validate_schema_caching,
        validate_json_extraction,
        validate_schema_validation,
        validate_typed_model_creation,
        validate_retry_logic,
        validate_prompt_executor_integration,
    ]
    checks: list[dict[str, Any]] = []
    for section in sections:
        checks.extend(section())
    failed = [item for item in checks if item["status"] == "FAIL"]
    return {
        "phase": PHASE,
        "model_version": MODEL_VERSION,
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "summary": {
            "total_checks": len(checks),
            "passed": len(checks) - len(failed),
            "failed": len(failed),
            "duration_s": round(time.perf_counter() - started, 3),
        },
    }


def main() -> int:
    report = run_validation()
    print(f"Phase: {report['phase']}")
    print(f"Model Version: {report['model_version']}")
    print(f"Status: {report['status']}")
    print(f"Checks: {report['summary']['passed']}/{report['summary']['total_checks']} PASS")
    for item in report["checks"]:
        if item["status"] == "FAIL":
            print(f"  FAIL: {item['name']} — {item.get('detail', '')}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
