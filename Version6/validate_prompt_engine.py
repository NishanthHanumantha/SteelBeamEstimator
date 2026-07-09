"""Phase LLM.1.1 — Prompt Management & Template Engine validation."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any
from unittest import mock

from src.llm.prompt_executor import PromptExecutor
from src.llm.prompts.prompt_manager import PromptManager
from src.llm.prompts.prompt_models import TemplateValidationError
from src.llm.prompts.prompt_registry import MODEL_VERSION, PHASE, PROMPT_REGISTRY, PromptRegistry
from src.llm.prompts.template_loader import TemplateLoader
from src.llm.prompts.template_renderer import TemplateRenderer
from src.llm.prompts.template_validator import TemplateValidator


def _check(name: str, passed: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def validate_templates_discovered() -> list[dict[str, Any]]:
    checks = [_check("Registry populated", len(PROMPT_REGISTRY) >= 9, f"count={len(PROMPT_REGISTRY)}")]
    for name, entry in PROMPT_REGISTRY.items():
        checks.append(
            _check(
                f"Template exists {name}",
                entry.absolute_path.exists(),
                str(entry.absolute_path),
            )
        )
    return checks


def validate_registry_loads() -> list[dict[str, Any]]:
    checks = []
    for name in PROMPT_REGISTRY:
        entry = PromptRegistry.get(name)
        checks.append(_check(f"Registry resolves {name}", entry.template_name == name))
        checks.append(_check(f"Registry path valid {name}", entry.absolute_path.exists()))
    return checks


def validate_markdown_and_metadata() -> list[dict[str, Any]]:
    loader = TemplateLoader()
    checks = []
    for name, entry in PROMPT_REGISTRY.items():
        loaded = loader.load(entry)
        checks.append(_check(f"Markdown loads {name}", bool(loaded.body.strip())))
        checks.append(_check(f"Metadata parsed {name}", loaded.metadata.name != ""))
        checks.append(_check(f"Metadata version {name}", loaded.metadata.version != ""))
        checks.append(_check(f"Checksum generated {name}", len(loaded.checksum) == 64))
    return checks


def validate_variable_replacement() -> list[dict[str, Any]]:
    rendered = TemplateRenderer.render("Beam {{beam_name}}", {"beam_name": "B12"})
    checks = [
        _check("Variable replacement works", rendered == "Beam B12", rendered),
        _check("No expression evaluation", "{{" not in rendered),
    ]
    manager = PromptManager()
    prompt = manager.get_prompt(
        "SAMPLE_PROMPT",
        {
            "expected_response": "Prompt Engine OK",
            "template_name": "SAMPLE_PROMPT",
        },
    )
    checks.append(_check("PromptManager renders template", "Prompt Engine OK" in prompt.rendered_prompt))
    checks.append(_check("Rendered prompt stored", bool(prompt.rendered_prompt)))
    return checks


def validate_template_validation() -> list[dict[str, Any]]:
    checks = []
    try:
        TemplateValidator.validate("")
        checks.append(_check("Empty template rejected", False))
    except TemplateValidationError:
        checks.append(_check("Empty template rejected", True))

    try:
        TemplateValidator.validate("Hello {{missing}}", {}, require_resolved=True)
        checks.append(_check("Unresolved variable rejected", False))
    except TemplateValidationError:
        checks.append(_check("Unresolved variable rejected", True))

    TemplateValidator.validate("Valid template {{name}}", {"name": "OK"})
    checks.append(_check("Valid template accepted", True))
    return checks


def validate_cache() -> list[dict[str, Any]]:
    loader = TemplateLoader()
    entry = PromptRegistry.get("SAMPLE_PROMPT")
    first = loader.load(entry)
    second = loader.load(entry)
    return [
        _check("Cache returns loaded template", bool(first.body)),
        _check("Cache key stable on reload", first.cache_key == second.cache_key),
        _check("Checksum stable on reload", first.checksum == second.checksum),
    ]


def validate_prompt_executor_integration() -> list[dict[str, Any]]:
    checks = []
    manager = PromptManager()
    prompt = manager.get_prompt(
        "SAMPLE_PROMPT",
        {"expected_response": "Prompt Engine OK", "template_name": "SAMPLE_PROMPT"},
    )

    executor = PromptExecutor()
    with mock.patch.object(executor._client, "generate_response", return_value="Prompt Engine OK") as mocked:
        result = executor.execute_template(
            "SAMPLE_PROMPT",
            {"expected_response": "Prompt Engine OK", "template_name": "SAMPLE_PROMPT"},
            system_template="ENGINEERING_SYSTEM",
        )
        checks.append(_check("execute_template returns text", result == "Prompt Engine OK"))
        checks.append(_check("execute_template calls Claude client", mocked.called))
        checks.append(
            _check(
                "execute_template passes rendered prompt",
                mocked.call_args[0][0] == prompt.rendered_prompt,
            )
        )

    with mock.patch.object(executor._client, "generate_response", return_value="Legacy OK") as mocked_legacy:
        legacy = executor.execute(user_prompt="Legacy OK")
        checks.append(_check("execute() backward compatible", legacy == "Legacy OK"))
        checks.append(_check("execute() still calls Claude client", mocked_legacy.called))
    return checks


def run_validation() -> dict[str, Any]:
    started = time.perf_counter()
    sections = [
        validate_templates_discovered,
        validate_registry_loads,
        validate_markdown_and_metadata,
        validate_variable_replacement,
        validate_template_validation,
        validate_cache,
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
