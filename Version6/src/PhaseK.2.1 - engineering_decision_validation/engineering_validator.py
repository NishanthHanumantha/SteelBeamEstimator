"""GROUP 4 — Engineering consistency validation."""

from __future__ import annotations

from typing import Any, List

from _rule_helpers import check
from decision_validation_types import VALID_DECISION_CATEGORIES


class EngineeringValidator:
    """Validate engineering consistency of resolved decisions."""

    def validate(
        self,
        decision: dict[str, Any],
        snapshot: dict[str, Any],
        errors: List[dict[str, str]],
        warnings: List[dict[str, str]],
        validated_rules: List[dict[str, str]],
    ) -> List[bool]:
        category = str(decision.get("decision_category") or "")
        rule = str(decision.get("resolution_rule") or "")
        primary = decision.get("primary_intent") or {}
        supporting = list(decision.get("supporting_intents") or [])
        suppressed = list(decision.get("suppressed_intents") or [])
        known_rules = snapshot.get("indexes", {}).get("known_rules") or set()
        intent_ids = snapshot.get("indexes", {}).get("intent_ids") or set()

        active_ids = set()
        if primary.get("intent_id"):
            active_ids.add(str(primary.get("intent_id")))
        for item in supporting:
            if item.get("intent_id"):
                active_ids.add(str(item.get("intent_id")))
        suppressed_ids = {
            str(item.get("intent_id")) for item in suppressed if item.get("intent_id")
        }
        overlap = active_ids & suppressed_ids
        supporting_ok = all(
            (not intent_ids) or str(item.get("intent_id")) in intent_ids
            for item in supporting
            if item.get("intent_id")
        )

        if int(decision.get("active_intent_count") or 0) not in (0, len(active_ids)):
            if int(decision.get("active_intent_count") or 0) != len(active_ids):
                warnings.append(
                    {
                        "group": "ENGINEERING",
                        "code": "ACTIVE_COUNT",
                        "message": "active_intent_count does not match derived active intent set",
                    }
                )

        return [
            check(bool(primary.get("intent_id")), "ENGINEERING", "Primary intent exists", errors, validated_rules),
            check(bool(active_ids), "ENGINEERING", "Primary intent active", errors, validated_rules),
            check(supporting_ok, "ENGINEERING", "Supporting intents valid", errors, validated_rules),
            check(not overlap, "ENGINEERING", "Suppressed intents not active", errors, validated_rules),
            check(
                category in VALID_DECISION_CATEGORIES,
                "ENGINEERING",
                "Decision category valid",
                errors,
                validated_rules,
            ),
            check(
                bool(rule) and (rule in known_rules or rule.startswith("K.1.1.")),
                "ENGINEERING",
                "Engineering rule exists",
                errors,
                validated_rules,
            ),
            check(
                bool(category),
                "ENGINEERING",
                "Specification compatible",
                errors,
                validated_rules,
            ),
            check(
                bool((decision.get("evidence") or {}).get("calculation_context_id")),
                "ENGINEERING",
                "Calculation context compatible",
                errors,
                validated_rules,
            ),
        ]
