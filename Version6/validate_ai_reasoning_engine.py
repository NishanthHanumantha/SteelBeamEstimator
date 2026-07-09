"""Phase AI.1 — Engineering Reasoning Engine validation."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any
from unittest import mock

from src.ai import (
    MODEL_VERSION,
    PHASE,
    PHASE_AI_1_DIR,
    AnnotationReasoningResult,
    BeamReasoningResult,
    EngineeringReasoningEngine,
    EngineeringReasoningResult,
    QAReasoningResult,
    ReinforcementReasoningResult,
)

sys.path.insert(0, str(PHASE_AI_1_DIR))

from confidence_engine import ConfidenceEngine  # noqa: E402
from reasoning_cache import ReasoningCache  # noqa: E402
from reasoning_context_mapper import ReasoningContextMapper  # noqa: E402
from reasoning_exceptions import ReasoningValidationError  # noqa: E402
from reasoning_logger import ReasoningLogger  # noqa: E402
from reasoning_metrics import ReasoningMetricsCollector  # noqa: E402
from reasoning_models import OUTPUT_DIR  # noqa: E402
from reasoning_registry import ReasoningRegistry, TaskRegistry  # noqa: E402
from reasoning_result_builder import ReasoningResultBuilder  # noqa: E402
from reasoning_validator import ReasoningValidator  # noqa: E402
from src.llm.context.engineering_context_builder import EngineeringContextBuilder  # noqa: E402
from src.llm.json_engine.response_models import StructuredResponse  # noqa: E402
from src.llm.prompt_executor import PromptExecutor  # noqa: E402


SAMPLE_OBJECTS: dict[str, Any] = {
    "beams": [{"beam_id": "B-101", "span_m": 6.5, "section": "W12x26"}],
    "reinforcement": {"bar_count": 12, "bars": [{"bar_id": "R-1", "diameter_mm": 16}]},
    "general_notes": {"project_information": {"project_name": "Validation Tower"}},
    "calculation_context": [
        {
            "context_id": "CTX-1",
            "beam_id": "B-101",
            "concrete_grade": "C30",
            "steel_grade": "Grade 60",
            "calculation_status": "complete",
        }
    ],
    "geometry": {"beam_node_count": 8, "support_node_count": 4, "edge_count": 12},
    "supports": [{"support_id": "S-1", "beam_id": "B-101"}],
    "dimensions": [{"beam_id": "B-101", "length_mm": 6500}],
    "material_properties": {"yield_strength_mpa": 420},
    "engineering_graph": {"project_id": "P-1", "node_count": 20, "edge_count": 30},
    "beam_schedule": [{"beam_id": "B-101", "context_id": "CTX-1"}],
}

MOCK_RESPONSES = {
    "BEAM_REASONING": (
        '{"beam_id":"B-101","beam_name":"B-101","reasoning":"Beam span aligns with support layout.",'
        '"confidence":0.91,"evidence":["beam context present"]}'
    ),
    "ANNOTATION_CLASSIFICATION": (
        '{"annotation_id":"A-1","region_id":"R-1","interpretation":"Stirrup spacing annotation.",'
        '"confidence":0.88}'
    ),
    "REINFORCEMENT_INTERPRETATION": (
        '{"beam_id":"B-101","annotation_text":"4T16","parsed_result":{"bars":4,"size":16},'
        '"confidence":0.87}'
    ),
    "QA_REASONING": (
        '{"artifact_name":"beam_schedule","validation_status":"PASS","issues":[],"confidence":0.92}'
    ),
    "GENERAL_ENGINEERING_REASONING": (
        '{"status":"ok","confidence":0.85,"message":"General engineering context is coherent."}'
    ),
}


def _check(name: str, passed: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def validate_task_registry() -> list[dict[str, Any]]:
    checks = [_check("Task registry populated", len(TaskRegistry.all_task_types()) >= 5)]
    for task_type in TaskRegistry.all_task_types():
        task = TaskRegistry.get(task_type)
        checks.append(_check(f"Task registered {task_type}", task.task_type == task_type))
        checks.append(_check(f"Task has template {task_type}", bool(task.prompt_template)))
        checks.append(_check(f"Task has schema {task_type}", bool(task.schema_name)))
        checks.append(_check(f"Task has result model {task_type}", bool(task.result_model)))
    checks.append(_check("Reasoning registry exposes models", len(ReasoningRegistry.result_models()) >= 5))
    return checks


def validate_context_mapping() -> list[dict[str, Any]]:
    builder = EngineeringContextBuilder()
    mapper = ReasoningContextMapper(builder)
    context = builder.build_context("BEAM_REASONING", SAMPLE_OBJECTS)
    mapped = mapper.map(context, {"beam_id": "B-101", "beam_name": "B-101"}, task_type="BEAM_REASONING")
    return [
        _check("Context mapping includes engineering_context", "engineering_context" in mapped),
        _check("Context mapping includes reasoning constraints", "reasoning_constraints" in mapped),
        _check("Context mapping includes section variables", "context_beam" in mapped),
        _check("Beam section extractable", mapper.extract_section(context, "beam") is not None),
    ]


def validate_confidence_engine() -> list[dict[str, Any]]:
    checks = [
        _check("Numeric confidence accepted", ConfidenceEngine.normalize(0.91) == 0.91),
        _check("High label normalized", ConfidenceEngine.normalize("High") == 0.82),
        _check("Confidence classified", ConfidenceEngine.classify(0.91) == "Very High"),
    ]
    try:
        ConfidenceEngine.normalize(1.5)
        checks.append(_check("Out-of-range confidence rejected", False))
    except ReasoningValidationError:
        checks.append(_check("Out-of-range confidence rejected", True))
    return checks


def validate_result_builder() -> list[dict[str, Any]]:
    builder = ReasoningResultBuilder()
    structured = StructuredResponse(
        schema_name="BEAM_REASONING",
        schema_version="1.0",
        raw_json={
            "beam_id": "B-101",
            "beam_name": "B-101",
            "reasoning": "Beam reasoning summary.",
            "confidence": 0.9,
            "evidence": ["evidence-1"],
        },
        validated_data={
            "beam_id": "B-101",
            "beam_name": "B-101",
            "reasoning": "Beam reasoning summary.",
            "confidence": 0.9,
            "evidence": ["evidence-1"],
        },
        confidence=0.9,
    )
    result = builder.build("BEAM_REASONING", structured, context_checksum="abc", template_version="1.0")
    return [
        _check("Beam reasoning result built", isinstance(result, BeamReasoningResult)),
        _check("Result has summary", bool(result.summary)),
        _check("Result has checksum", bool(result.checksum)),
        _check("Result has reasoning_id", bool(result.reasoning_id)),
    ]


def validate_reasoning_validator() -> list[dict[str, Any]]:
    builder = ReasoningResultBuilder()
    structured = StructuredResponse(
        schema_name="BEAM_REASONING",
        schema_version="1.0",
        raw_json={"beam_id": "B-101", "reasoning": "ok", "confidence": 0.8},
        validated_data={"beam_id": "B-101", "reasoning": "ok", "confidence": 0.8},
        confidence=0.8,
    )
    valid = builder.build("BEAM_REASONING", structured, context_checksum="abc", template_version="1.0")
    validator = ReasoningValidator()
    checks = []
    try:
        validator.validate(valid)
        checks.append(_check("Valid reasoning accepted", True))
    except ReasoningValidationError as exc:
        checks.append(_check("Valid reasoning accepted", False, str(exc)))

    invalid = valid
    invalid.summary = ""
    try:
        validator.validate(invalid)
        checks.append(_check("Empty summary rejected", False))
    except ReasoningValidationError:
        checks.append(_check("Empty summary rejected", True))
    return checks


def validate_cache() -> list[dict[str, Any]]:
    cache = ReasoningCache()
    key = cache.build_key("BEAM_REASONING", "checksum-1", "1.0")
    builder = ReasoningResultBuilder()
    structured = StructuredResponse(
        schema_name="BEAM_REASONING",
        schema_version="1.0",
        raw_json={"beam_id": "B-101", "reasoning": "cached", "confidence": 0.8},
        validated_data={"beam_id": "B-101", "reasoning": "cached", "confidence": 0.8},
        confidence=0.8,
    )
    result = builder.build("BEAM_REASONING", structured, context_checksum="checksum-1", template_version="1.0")
    cache.set(key, result)
    return [
        _check("Cache stores result", cache.get(key) is not None),
        _check("Cache hit increments", cache.statistics()["cache_hits"] == 1),
        _check("Cache key deterministic", key == cache.build_key("BEAM_REASONING", "checksum-1", "1.0")),
    ]


def validate_metrics_and_logging() -> list[dict[str, Any]]:
    metrics = ReasoningMetricsCollector()
    logger = ReasoningLogger()
    return [
        _check("Metrics collector available", metrics is not None),
        _check("Logger available", logger is not None),
    ]


def _build_engine() -> EngineeringReasoningEngine:
    from reasoning_manager import ReasoningManager

    return EngineeringReasoningEngine(
        manager=ReasoningManager(
            prompt_executor=PromptExecutor(),
            cache=ReasoningCache(),
        )
    )


def validate_engine_integration() -> list[dict[str, Any]]:
    engine = _build_engine()
    mock_payload = MOCK_RESPONSES["BEAM_REASONING"]
    with mock.patch.object(engine._manager._prompt_executor._client, "generate_response", return_value=mock_payload):
        result = engine.reason(
            "BEAM_REASONING",
            SAMPLE_OBJECTS,
            {"beam_id": "B-101", "beam_name": "B-101"},
        )
    return [
        _check("EngineeringReasoningEngine returns result", isinstance(result, BeamReasoningResult)),
        _check("Result confidence valid", 0.0 <= result.confidence <= 1.0),
        _check("Result summary populated", bool(result.summary)),
    ]


def validate_output_generation() -> list[dict[str, Any]]:
    engine = _build_engine()
    mock_payload = MOCK_RESPONSES["BEAM_REASONING"]
    with mock.patch.object(engine._manager._prompt_executor._client, "generate_response", return_value=mock_payload):
        engine.reason("BEAM_REASONING", SAMPLE_OBJECTS, {"beam_id": "B-101", "beam_name": "B-101"})

    expected_files = [
        "reasoning_results.json",
        "reasoning_metrics.json",
        "reasoning_logs.json",
        "validation_report.json",
        "cache_statistics.json",
    ]
    checks = [_check("Output folder created", OUTPUT_DIR.exists())]
    for filename in expected_files:
        path = OUTPUT_DIR / filename
        checks.append(_check(f"Output file written {filename}", path.exists()))
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            checks.append(_check(f"Output JSON valid {filename}", isinstance(payload, dict)))
    return checks


def validate_deterministic_behaviour() -> list[dict[str, Any]]:
    engine_a = _build_engine()
    engine_b = _build_engine()
    mock_payload = MOCK_RESPONSES["BEAM_REASONING"]
    with mock.patch.object(engine_a._manager._prompt_executor._client, "generate_response", return_value=mock_payload):
        result_a = engine_a.reason("BEAM_REASONING", SAMPLE_OBJECTS, {"beam_id": "B-101", "beam_name": "B-101"})
    with mock.patch.object(engine_b._manager._prompt_executor._client, "generate_response", return_value=mock_payload):
        result_b = engine_b.reason("BEAM_REASONING", SAMPLE_OBJECTS, {"beam_id": "B-101", "beam_name": "B-101"})
    return [
        _check("Reasoning id deterministic", result_a.reasoning_id == result_b.reasoning_id),
        _check("Reasoning checksum deterministic", result_a.checksum == result_b.checksum),
        _check("Typed subclasses available", issubclass(BeamReasoningResult, EngineeringReasoningResult)),
        _check("Annotation subclass available", issubclass(AnnotationReasoningResult, EngineeringReasoningResult)),
        _check("Reinforcement subclass available", issubclass(ReinforcementReasoningResult, EngineeringReasoningResult)),
        _check("QA subclass available", issubclass(QAReasoningResult, EngineeringReasoningResult)),
    ]


def validate_all_task_types() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for task_type, mock_payload in MOCK_RESPONSES.items():
        engine = _build_engine()
        variables = {"beam_id": "B-101", "beam_name": "B-101", "annotation_id": "A-1", "region_id": "R-1"}
        with mock.patch.object(engine._manager._prompt_executor._client, "generate_response", return_value=mock_payload):
            result = engine.reason(task_type, SAMPLE_OBJECTS, variables)
        checks.append(_check(f"Task executes {task_type}", isinstance(result, EngineeringReasoningResult)))
    return checks


def run_validation() -> dict[str, Any]:
    started = time.perf_counter()
    sections = [
        validate_task_registry,
        validate_context_mapping,
        validate_confidence_engine,
        validate_result_builder,
        validate_reasoning_validator,
        validate_cache,
        validate_metrics_and_logging,
        validate_engine_integration,
        validate_output_generation,
        validate_deterministic_behaviour,
        validate_all_task_types,
    ]
    checks: list[dict[str, Any]] = []
    for section in sections:
        checks.extend(section())
    failed = [item for item in checks if item["status"] == "FAIL"]
    report = {
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
        "output_dir": str(OUTPUT_DIR),
        "source_dir": str(PHASE_AI_1_DIR),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "validation_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    report = run_validation()
    print(f"Phase: {report['phase']}")
    print(f"Model Version: {report['model_version']}")
    print(f"Status: {report['status']}")
    print(f"Checks: {report['summary']['passed']}/{report['summary']['total_checks']} PASS")
    print(f"Output Dir: {report['output_dir']}")
    for item in report["checks"]:
        if item["status"] == "FAIL":
            print(f"  FAIL: {item['name']} — {item.get('detail', '')}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
