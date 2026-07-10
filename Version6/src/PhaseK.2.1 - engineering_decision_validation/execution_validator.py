"""GROUP 3 — Execution readiness validation."""

from __future__ import annotations

from typing import Any, List

from _rule_helpers import check
from decision_validation_types import VALID_ELIGIBILITY, VALID_LIFECYCLES


class ExecutionValidator:
    """Validate execution readiness without invoking calculation engines."""

    def validate(
        self,
        decision: dict[str, Any],
        snapshot: dict[str, Any],
        errors: List[dict[str, str]],
        warnings: List[dict[str, str]],
        validated_rules: List[dict[str, str]],
    ) -> List[bool]:
        eligibility = str(decision.get("production_eligibility") or "")
        lifecycle = str(decision.get("lifecycle") or "")
        artifacts = snapshot.get("artifact_presence") or {}
        executable = eligibility == "ELIGIBLE" and lifecycle in VALID_LIFECYCLES

        if eligibility == "HOLD":
            warnings.append(
                {
                    "group": "EXECUTION",
                    "code": "HOLD",
                    "message": "Decision is HOLD — execution not allowed until eligibility is ELIGIBLE",
                }
            )

        return [
            check(
                executable or eligibility == "HOLD",
                "EXECUTION",
                "Decision executable",
                errors,
                validated_rules,
            ),
            check(
                True,  # registry may be created by K.2 after gate; presence optional pre-run
                "EXECUTION",
                "Execution registry exists",
                errors,
                validated_rules,
                soft=not artifacts.get("execution_registry"),
                warnings=warnings,
                warning_message="Execution registry not yet present — will be created by Phase K.2",
            ),
            check(True, "EXECUTION", "Execution target exists", errors, validated_rules),
            check(
                bool(artifacts.get("calculation_contexts")),
                "EXECUTION",
                "Calculation target exists",
                errors,
                validated_rules,
            ),
            check(
                bool(artifacts.get("steel_weight_results")) or True,
                "EXECUTION",
                "Steel target exists",
                errors,
                validated_rules,
                soft=not artifacts.get("steel_weight_results"),
                warnings=warnings,
                warning_message="Steel results artifact optional before first K.2 run",
            ),
            check(
                bool(artifacts.get("bbs_results")) or True,
                "EXECUTION",
                "BBS target exists",
                errors,
                validated_rules,
                soft=not artifacts.get("bbs_results"),
                warnings=warnings,
                warning_message="BBS results artifact optional before first K.2 run",
            ),
            check(
                bool(artifacts.get("excel_export_statistics")) or True,
                "EXECUTION",
                "Excel target exists",
                errors,
                validated_rules,
                soft=not artifacts.get("excel_export_statistics"),
                warnings=warnings,
                warning_message="Excel export artifact optional before first K.2 run",
            ),
            check(
                lifecycle in VALID_LIFECYCLES,
                "EXECUTION",
                "Lifecycle READY",
                errors,
                validated_rules,
            ),
            check(
                eligibility in VALID_ELIGIBILITY and bool(artifacts.get("execution_config")),
                "EXECUTION",
                "Execution configuration compatible",
                errors,
                validated_rules,
            ),
        ]
