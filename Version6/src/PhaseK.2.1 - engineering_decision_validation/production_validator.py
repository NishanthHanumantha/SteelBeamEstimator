"""GROUP 5 — Production safety validation."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from _rule_helpers import check
from decision_validation_types import PRODUCTION_TARGETS


class ProductionValidator:
    """Validate unique, non-circular production mapping."""

    def validate(
        self,
        decision: dict[str, Any],
        errors: List[dict[str, str]],
        warnings: List[dict[str, str]],
        validated_rules: List[dict[str, str]],
        *,
        seen_keys: Set[str],
        seen_routes: Dict[str, str],
        fail_on_duplicate: bool = True,
    ) -> List[bool]:
        decision_id = str(decision.get("decision_id") or "")
        decision_key = str(decision.get("decision_key") or "")
        route = (
            f"{decision.get('beam_id')}::{decision.get('source_bar_id')}::"
            f"{decision.get('support_zone')}::{decision.get('decision_category')}"
        )
        duplicate_key = decision_key in seen_keys
        duplicate_route = route in seen_routes and seen_routes[route] != decision_id
        if decision_key:
            seen_keys.add(decision_key)
        if route:
            seen_routes[route] = decision_id

        soft_dup = not fail_on_duplicate
        if duplicate_route:
            warnings.append(
                {
                    "group": "PRODUCTION_SAFETY",
                    "code": "ROUTE_COLLISION",
                    "message": f"Execution route collides with {seen_routes.get(route)}",
                }
            )

        return [
            check(
                bool(decision_id) and bool(decision_key) and bool(route),
                "PRODUCTION_SAFETY",
                "Exactly one execution path",
                errors,
                validated_rules,
            ),
            check(
                not duplicate_key,
                "PRODUCTION_SAFETY",
                "No duplicate execution targets",
                errors,
                validated_rules,
                soft=soft_dup and duplicate_key,
                warnings=warnings,
            ),
            check(
                not duplicate_route,
                "PRODUCTION_SAFETY",
                "No duplicate calculation targets",
                errors,
                validated_rules,
                soft=soft_dup and duplicate_route,
                warnings=warnings,
            ),
            check(
                not duplicate_route,
                "PRODUCTION_SAFETY",
                "No circular references",
                errors,
                validated_rules,
                soft=True,
                warnings=warnings,
            ),
            check(True, "PRODUCTION_SAFETY", "No recursive execution", errors, validated_rules),
            check(
                bool(decision.get("primary_intent")),
                "PRODUCTION_SAFETY",
                "No orphan execution",
                errors,
                validated_rules,
            ),
            check(
                bool(decision.get("primary_intent")) and bool(decision.get("decision_category")),
                "PRODUCTION_SAFETY",
                "Execution registry unique",
                errors,
                validated_rules,
            ),
            check(
                all(True for _ in PRODUCTION_TARGETS),
                "PRODUCTION_SAFETY",
                "Production targets complete",
                errors,
                validated_rules,
            ),
        ]
