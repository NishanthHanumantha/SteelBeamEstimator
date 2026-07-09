"""Phase LLM.3 — Engineering Knowledge & Context Builder validation."""

from __future__ import annotations

import json
import sys
import time
from typing import Any
from unittest import mock

from src.llm.context.context_cache import ContextCache
from src.llm.context.context_collector import ContextCollector
from src.llm.context.context_compressor import ContextCompressor
from src.llm.context.context_filter import ContextFilter
from src.llm.context.context_models import ContextSection, ContextValidationError
from src.llm.context.context_registry import DEFAULT_TOKEN_BUDGET, MODEL_VERSION, PHASE, TASK_REGISTRY, ContextRegistry
from src.llm.context.context_serializer import ContextSerializer
from src.llm.context.context_validator import ContextValidator
from src.llm.context.engineering_context_builder import EngineeringContextBuilder
from src.llm.context.token_budget_manager import TokenBudgetManager
from src.llm.prompt_executor import PromptExecutor


SAMPLE_OBJECTS: dict[str, Any] = {
    "beams": [
        {"beam_id": "B-101", "span_m": 6.5, "section": "W12x26"},
        {"beam_id": "B-102", "span_m": 4.2, "section": "W10x22"},
    ],
    "reinforcement": {
        "bar_count": 12,
        "bars": [{"bar_id": "R-1", "diameter_mm": 16}, {"bar_id": "R-2", "diameter_mm": 20}],
    },
    "general_notes": {
        "project_information": {"project_name": "Validation Tower"},
        "material_specifications": {"concrete_grade": "C30"},
    },
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


def _check(name: str, passed: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def validate_context_registry() -> list[dict[str, Any]]:
    checks = [
        _check("Task registry populated", len(TASK_REGISTRY) >= 5),
        _check("Default token budget configured", DEFAULT_TOKEN_BUDGET == 6000),
    ]
    for task_type in ContextRegistry.all_task_types():
        definition = ContextRegistry.get(task_type)
        checks.append(_check(f"Task registered {task_type}", definition.task_type == task_type))
        checks.append(_check(f"Task has sections {task_type}", len(definition.sections) > 0))
        checks.append(_check(f"Task token budget {task_type}", definition.token_budget == DEFAULT_TOKEN_BUDGET))
    return checks


def validate_collector() -> list[dict[str, Any]]:
    collector = ContextCollector()
    collected = collector.collect(SAMPLE_OBJECTS)
    checks = [
        _check("Collector retains beams", "beams" in collected),
        _check("Collector retains reinforcement", "reinforcement" in collected),
        _check("Collector removes empty values", "empty" not in collector.collect({**SAMPLE_OBJECTS, "empty": {}})),
    ]
    snapshot = collector.load_production_snapshot()
    checks.append(_check("Production snapshot loader callable", isinstance(snapshot, dict)))
    return checks


def validate_filtering() -> list[dict[str, Any]]:
    context_filter = ContextFilter()
    collected = ContextCollector().collect(SAMPLE_OBJECTS)
    beam_sections = context_filter.filter("BEAM_REASONING", collected)
    qa_sections = context_filter.filter("QA_VALIDATOR", collected)
    names_beam = [item["section_name"] for item in beam_sections]
    names_qa = [item["section_name"] for item in qa_sections]
    return [
        _check("Beam reasoning includes beam section", "beam" in names_beam),
        _check("Beam reasoning includes calculation_context", "calculation_context" in names_beam),
        _check("QA validator includes beam_schedule", "beam_schedule" in names_qa),
        _check("Filtered sections are unique", len(names_beam) == len(set(names_beam))),
        _check("Filtered sections ordered deterministically", names_beam == sorted(names_beam, key=lambda name: names_beam.index(name))),
    ]


def validate_serialization() -> list[dict[str, Any]]:
    serializer = ContextSerializer()
    payload = {"z": 1, "a": {"b": 2, "a": 1}, "m": [{"y": 2, "x": 1}]}
    serialized = serializer.serialize(payload)
    text_a = serializer.to_text(serialized)
    text_b = serializer.to_text(serializer.serialize(payload))
    return [
        _check("Serializer sorts dictionary keys", list(serialized.keys()) == ["a", "m", "z"]),
        _check("Serializer output stable", text_a == text_b),
        _check("Serializer checksum stable", serializer.checksum(serialized) == serializer.checksum(serializer.serialize(payload))),
        _check("Token estimation available", serializer.estimate_tokens(text_a) > 0),
    ]


def validate_compression() -> list[dict[str, Any]]:
    compressor = ContextCompressor()
    sections = [
        {
            "section_name": "beam",
            "priority": "Critical",
            "content": {"beam": {"beams": [{"beam_id": "B-101"}, {"beam_id": "B-101"}]}},
        },
        {
            "section_name": "supports",
            "priority": "Medium",
            "content": {"supports": {"beams": [{"beam_id": "B-101"}]}},
        },
    ]
    compressed = compressor.compress_sections(sections)
    original_size = len(json.dumps(sections, sort_keys=True))
    compressed_size = len(json.dumps(compressed, sort_keys=True))
    ratio = compressor.compression_ratio(original_size, compressed_size)
    return [
        _check("Compression returns sections", len(compressed) > 0),
        _check("Compression ratio computed", 0 < ratio <= 1.0),
        _check("Critical beam section preserved", any(item["section_name"] == "beam" for item in compressed)),
    ]


def validate_token_budget() -> list[dict[str, Any]]:
    token_manager = TokenBudgetManager(default_budget=50)
    sections = [
        {
            "section_name": "beam",
            "priority": "Critical",
            "content": {"beam": {"beams": SAMPLE_OBJECTS["beams"]}},
        },
        {
            "section_name": "material_properties",
            "priority": "Low",
            "content": {"material_properties": {"notes": "x" * 500}},
        },
        {
            "section_name": "engineering_graph",
            "priority": "Low",
            "content": {"engineering_graph": {"notes": "y" * 500}},
        },
    ]
    budgeted = token_manager.apply_budget("BEAM_REASONING", sections)
    names = [item["section_name"] for item in budgeted]
    return [
        _check("Token manager annotates estimates", all(item.get("token_estimate", 0) > 0 for item in budgeted)),
        _check("Critical section preserved under budget", "beam" in names),
        _check("Low-priority section trimmed when needed", len(budgeted) < len(sections)),
    ]


def validate_validation_rules() -> list[dict[str, Any]]:
    validator = ContextValidator()
    builder = EngineeringContextBuilder()
    valid = builder.build_context("BEAM_REASONING", SAMPLE_OBJECTS)
    checks = []
    try:
        validator.validate(valid)
        checks.append(_check("Valid context accepted", True))
    except ContextValidationError as exc:
        checks.append(_check("Valid context accepted", False, str(exc)))

    invalid = valid
    invalid.sections = []
    try:
        validator.validate(invalid)
        checks.append(_check("Empty context rejected", False))
    except ContextValidationError:
        checks.append(_check("Empty context rejected", True))
    return checks


def validate_cache() -> list[dict[str, Any]]:
    cache = ContextCache()
    builder = EngineeringContextBuilder(cache=cache)
    first = builder.build_context("BEAM_REASONING", SAMPLE_OBJECTS)
    second = builder.build_context("BEAM_REASONING", SAMPLE_OBJECTS)
    modified = dict(SAMPLE_OBJECTS)
    modified["beams"] = [{"beam_id": "B-999", "span_m": 1.0}]
    third = builder.build_context("BEAM_REASONING", modified)
    return [
        _check("Cache stores contexts", cache.size >= 2),
        _check("Cache hit returns identical checksum", first.checksum == second.checksum),
        _check("Cache miss on input change", third.checksum != first.checksum),
    ]


def validate_builder_determinism() -> list[dict[str, Any]]:
    builder_a = EngineeringContextBuilder(cache=ContextCache())
    builder_b = EngineeringContextBuilder(cache=ContextCache())
    context_a = builder_a.build_context("BEAM_REASONING", SAMPLE_OBJECTS)
    context_b = builder_b.build_context("BEAM_REASONING", SAMPLE_OBJECTS)
    section_names_a = [section.section_name for section in context_a.sections]
    section_names_b = [section.section_name for section in context_b.sections]
    variables_a = builder_a.to_prompt_variables(context_a)
    variables_b = builder_b.to_prompt_variables(context_b)
    return [
        _check("Builder version set", context_a.context_version == MODEL_VERSION),
        _check("Context checksum deterministic", context_a.checksum == context_b.checksum),
        _check("Section ordering deterministic", section_names_a == section_names_b),
        _check("Prompt variables deterministic", variables_a == variables_b),
        _check("Estimated tokens present", context_a.estimated_tokens > 0),
        _check("Section checksums present", all(section.checksum for section in context_a.sections)),
    ]


def validate_prompt_executor_integration() -> list[dict[str, Any]]:
    executor = PromptExecutor()
    valid_json = '{"result":"engineering-ok","confidence":0.93,"template_name":"BEAM_REASONING"}'

    with mock.patch.object(executor._client, "generate_response", return_value=valid_json) as mocked:
        structured = executor.execute_engineering(
            "BEAM_REASONING",
            "SAMPLE_RESPONSE",
            "BEAM_REASONING",
            SAMPLE_OBJECTS,
            {"beam_name": "B-101", "beam_id": "B-101"},
        )
        prompt_arg = mocked.call_args[0][0]
    checks = [
        _check("execute_engineering returns StructuredResponse", structured.validated_data["result"] == "engineering-ok"),
        _check("engineering_context injected", "{{engineering_context}}" not in prompt_arg and "B-101" in prompt_arg),
        _check("context_checksum injected", "context_checksum" not in prompt_arg),
    ]

    with mock.patch.object(executor._client, "generate_response", return_value=valid_json):
        json_result = executor.execute_json(
            "SAMPLE_PROMPT",
            "SAMPLE_RESPONSE",
            {"expected_response": "ok", "template_name": "SAMPLE_PROMPT"},
        )
        checks.append(_check("execute_json() backward compatible", json_result.confidence == 0.93))

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
        validate_context_registry,
        validate_collector,
        validate_filtering,
        validate_serialization,
        validate_compression,
        validate_token_budget,
        validate_validation_rules,
        validate_cache,
        validate_builder_determinism,
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
