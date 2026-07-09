"""Phase LLM.1 — Anthropic Claude integration validation."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

from dotenv import load_dotenv

from src.llm.claude_config import ClaudeConfig
from src.llm.claude_client import ClaudeClient, map_sdk_exception
from src.llm.exceptions import ClaudeAPIError, ClaudeAuthenticationError, ClaudeRateLimitError, ClaudeTimeoutError
from src.llm.prompt_executor import PromptExecutor


def _check(name: str, passed: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def validate_env_loading() -> list[dict[str, Any]]:
    dotenv_path = ClaudeConfig.DOTENV_PATH
    checks = [
        _check(
            ".env path configured",
            dotenv_path == Path(r"C:\Users\nishanth.h\SteelBeamEstimator\.env"),
            str(dotenv_path),
        ),
        _check(".env file exists", dotenv_path.exists(), str(dotenv_path)),
    ]
    if dotenv_path.exists():
        load_dotenv(dotenv_path, override=True)
        checks.append(
            _check(
                "ANTHROPIC_API_KEY detected",
                bool(os.getenv(ClaudeConfig.API_KEY_ENV)),
            )
        )
        try:
            from src.llm.claude_client import load_api_key

            load_api_key()
            checks.append(_check("load_api_key succeeds", True))
        except ClaudeAuthenticationError as exc:
            checks.append(_check("load_api_key succeeds", False, str(exc)))
    return checks


def validate_client_initialization() -> list[dict[str, Any]]:
    try:
        client = ClaudeClient()
        return [
            _check("Claude client initializes", True),
            _check("Anthropic SDK client attached", hasattr(client, "_client")),
        ]
    except ClaudeAuthenticationError as exc:
        return [_check("Claude client initializes", False, str(exc))]


def validate_live_request() -> list[dict[str, Any]]:
    try:
        started = time.perf_counter()
        response = PromptExecutor().execute(
            user_prompt="Reply with exactly: Claude Integration OK",
            system_prompt="Respond with plain text only.",
        )
        elapsed = time.perf_counter() - started
        return [
            _check("Simple API request succeeds", True),
            _check("Response received", bool(response)),
            _check("Response contains expected text", "Claude Integration OK" in response, response[:80]),
            _check("Execution time recorded", elapsed > 0, f"{elapsed:.3f}s"),
        ]
    except ClaudeAPIError as exc:
        return [
            _check("Simple API request succeeds", False, str(exc)),
            _check("Response received", False),
        ]


def validate_retry_logic() -> list[dict[str, Any]]:
    from anthropic import RateLimitError as SdkRateLimitError

    response_block = SimpleNamespace(text="retry-success")
    response = SimpleNamespace(content=[response_block])

    client = ClaudeClient()
    sdk_error = SdkRateLimitError("rate limited", response=mock.Mock(), body=None)
    with mock.patch.object(
        client._client.messages,
        "create",
        side_effect=[sdk_error, sdk_error, response],
    ) as create_mock:
        text = client.generate_response("retry-test")
        return [
            _check("Retry logic returns success", text == "retry-success"),
            _check("Retry attempts executed", create_mock.call_count == 3, f"calls={create_mock.call_count}"),
        ]


def validate_timeout_mapping() -> list[dict[str, Any]]:
    from anthropic import APITimeoutError

    mapped = map_sdk_exception(APITimeoutError("timeout"))
    return [_check("Timeout maps to ClaudeTimeoutError", isinstance(mapped, ClaudeTimeoutError))]


def validate_exception_mapping() -> list[dict[str, Any]]:
    from anthropic import APIStatusError, AuthenticationError, RateLimitError

    return [
        _check(
            "Authentication maps correctly",
            isinstance(
                map_sdk_exception(AuthenticationError("auth", response=mock.Mock(), body=None)),
                ClaudeAuthenticationError,
            ),
        ),
        _check(
            "Rate limit maps correctly",
            isinstance(
                map_sdk_exception(RateLimitError("rate", response=mock.Mock(), body=None)),
                ClaudeRateLimitError,
            ),
        ),
        _check(
            "Generic API status maps correctly",
            isinstance(
                map_sdk_exception(
                    APIStatusError("server", response=mock.Mock(status_code=500), body=None)
                ),
                ClaudeAPIError,
            ),
        ),
    ]


def validate_no_legacy_runtime_usage() -> list[dict[str, Any]]:
    root = Path(__file__).resolve().parent
    violations: list[str] = []
    skip_dirs = {"__pycache__", ".git", "data", "node_modules", "llm"}
    forbidden_imports = ("import openai", "from openai", "import deepseek", "from deepseek")
    forbidden_calls = ("OpenAI(", "client.chat.completions", "deepseek-chat", "deepseek-reasoner")

    for path in root.rglob("*.py"):
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.name in {"validate_claude_integration.py"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = str(path.relative_to(root))
        if "src\\llm" in rel or "src/llm" in rel:
            if "Anthropic(" not in text or path.name != "claude_client.py":
                pass
            continue
        for pattern in forbidden_imports + forbidden_calls:
            if pattern in text:
                violations.append(f"{rel}: {pattern}")
        if "Anthropic(" in text:
            violations.append(f"{rel}: Anthropic()")
        if "ANTROPIC_API_KEY" in text:
            violations.append(f"{rel}: ANTROPIC_API_KEY")

    return [
        _check(
            "No legacy provider runtime usage in Version6 Python files",
            not violations,
            "; ".join(violations[:10]) if violations else "Clean",
        )
    ]


def run_validation() -> dict[str, Any]:
    sections = [
        validate_env_loading,
        validate_client_initialization,
        validate_live_request,
        validate_retry_logic,
        validate_timeout_mapping,
        validate_exception_mapping,
        validate_no_legacy_runtime_usage,
    ]
    checks: list[dict[str, Any]] = []
    for section in sections:
        checks.extend(section())

    failed = [item for item in checks if item["status"] == "FAIL"]
    return {
        "phase": ClaudeConfig.PHASE,
        "model_version": ClaudeConfig.MODEL_VERSION,
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "summary": {
            "total_checks": len(checks),
            "passed": len(checks) - len(failed),
            "failed": len(failed),
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
