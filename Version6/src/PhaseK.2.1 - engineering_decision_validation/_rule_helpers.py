"""Shared deterministic check helpers for K.2.1 validators."""

from __future__ import annotations

from typing import Any, List


def require(
    value: Any,
    group: str,
    message: str,
    errors: List[dict[str, str]],
    validated_rules: List[dict[str, str]],
    *,
    soft: bool = False,
    warnings: List[dict[str, str]] | None = None,
    warning_message: str | None = None,
) -> bool:
    return check(
        bool(value),
        group,
        message,
        errors,
        validated_rules,
        soft=soft,
        warnings=warnings,
        warning_message=warning_message,
    )


def check(
    passed: bool,
    group: str,
    message: str,
    errors: List[dict[str, str]],
    validated_rules: List[dict[str, str]],
    *,
    soft: bool = False,
    warnings: List[dict[str, str]] | None = None,
    warning_message: str | None = None,
) -> bool:
    if passed:
        validated_rules.append({"group": group, "rule": message, "status": "PASS"})
        return True
    if soft and warnings is not None:
        warnings.append(
            {
                "group": group,
                "code": "SOFT_FAIL",
                "message": warning_message or message,
            }
        )
        validated_rules.append({"group": group, "rule": message, "status": "WARNING"})
        return True
    errors.append({"group": group, "code": "FAIL", "message": message})
    validated_rules.append({"group": group, "rule": message, "status": "FAIL"})
    return False


def score_group(checks: List[bool], weight: int) -> int:
    if not checks:
        return weight
    passed = sum(1 for item in checks if item)
    return int(round((passed / len(checks)) * weight))
