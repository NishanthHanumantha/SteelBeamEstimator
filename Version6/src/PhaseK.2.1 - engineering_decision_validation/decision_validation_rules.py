"""Orchestrate deterministic validation rule groups."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from decision_validation_types import SCORE_WEIGHTS
from engineering_validator import EngineeringValidator
from execution_validator import ExecutionValidator
from identity_validator import IdentityValidator
from production_validator import ProductionValidator
from _rule_helpers import score_group
from traceability_validator import TraceabilityValidator
from version_validator import VersionValidator


class DecisionValidationRules:
    """Compose group validators into a single read-only evaluation."""

    def __init__(self) -> None:
        self._identity = IdentityValidator()
        self._traceability = TraceabilityValidator()
        self._execution = ExecutionValidator()
        self._engineering = EngineeringValidator()
        self._production = ProductionValidator()
        self._version = VersionValidator()

    def evaluate(
        self,
        decision: dict[str, Any],
        snapshot: dict[str, Any],
        *,
        seen_keys: Set[str],
        seen_routes: Dict[str, str],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        config = config or {}
        errors: List[dict[str, str]] = []
        warnings: List[dict[str, str]] = []
        validated_rules: List[dict[str, str]] = []
        breakdown: Dict[str, int] = {}

        breakdown["IDENTITY"] = score_group(
            self._identity.validate(decision, snapshot, errors, warnings, validated_rules),
            SCORE_WEIGHTS["IDENTITY"],
        )
        breakdown["TRACEABILITY"] = score_group(
            self._traceability.validate(
                decision,
                snapshot,
                errors,
                warnings,
                validated_rules,
                fail_on_broken=bool(config.get("fail_on_broken_traceability", True)),
            ),
            SCORE_WEIGHTS["TRACEABILITY"],
        )
        breakdown["EXECUTION"] = score_group(
            self._execution.validate(decision, snapshot, errors, warnings, validated_rules),
            SCORE_WEIGHTS["EXECUTION"],
        )
        breakdown["ENGINEERING"] = score_group(
            self._engineering.validate(decision, snapshot, errors, warnings, validated_rules),
            SCORE_WEIGHTS["ENGINEERING"],
        )
        breakdown["PRODUCTION_SAFETY"] = score_group(
            self._production.validate(
                decision,
                errors,
                warnings,
                validated_rules,
                seen_keys=seen_keys,
                seen_routes=seen_routes,
                fail_on_duplicate=bool(config.get("fail_on_duplicate_execution", True)),
            ),
            SCORE_WEIGHTS["PRODUCTION_SAFETY"],
        )
        self._version.validate(decision, errors, warnings, validated_rules)
        breakdown["VERSION"] = 0

        total = sum(breakdown[key] for key in SCORE_WEIGHTS)
        return {
            "errors": errors,
            "warnings": warnings,
            "validated_rules": validated_rules,
            "score_breakdown": breakdown,
            "validation_score": total,
        }
