"""GROUP 1 — Identity validation."""

from __future__ import annotations

from typing import Any, List

from _rule_helpers import check, require


class IdentityValidator:
    """Validate decision identity fields and referenced identifiers."""

    def validate(
        self,
        decision: dict[str, Any],
        snapshot: dict[str, Any],
        errors: List[dict[str, str]],
        warnings: List[dict[str, str]],
        validated_rules: List[dict[str, str]],
    ) -> List[bool]:
        indexes = snapshot.get("indexes") or {}
        primary = decision.get("primary_intent") or {}
        evidence = decision.get("evidence") or {}
        object_id = str(decision.get("engineering_object_id") or "")
        intent_id = str(primary.get("intent_id") or evidence.get("primary_intent_id") or "")
        context_id = str(evidence.get("calculation_context_id") or "")
        beam_id = str(decision.get("beam_id") or "")
        intent_obj = (indexes.get("intent_by_id") or {}).get(intent_id) or {}
        spec_id = str(
            intent_obj.get("specification_id")
            or evidence.get("specification_id")
            or decision.get("decision_category")
            or ""
        )

        object_ids = indexes.get("engineering_object_ids") or set()
        intent_ids = indexes.get("intent_ids") or set()
        context_ids = indexes.get("context_ids") or set()
        beam_ids = indexes.get("beam_ids") or set()
        spec_ids = indexes.get("specification_ids") or set()

        return [
            require(decision.get("decision_id"), "IDENTITY", "Decision ID exists", errors, validated_rules),
            require(decision.get("decision_key"), "IDENTITY", "Decision Key exists", errors, validated_rules),
            check(
                bool(object_id) and (not object_ids or object_id in object_ids),
                "IDENTITY",
                "Engineering Object exists",
                errors,
                validated_rules,
            ),
            check(
                bool(intent_id) and (not intent_ids or intent_id in intent_ids),
                "IDENTITY",
                "Intent exists",
                errors,
                validated_rules,
            ),
            check(
                bool(beam_id) and (not beam_ids or beam_id in beam_ids),
                "IDENTITY",
                "Beam exists",
                errors,
                validated_rules,
            ),
            check(
                bool(context_id) and (not context_ids or context_id in context_ids),
                "IDENTITY",
                "Calculation Context exists",
                errors,
                validated_rules,
            ),
            check(
                bool(spec_id) and (not spec_ids or spec_id in spec_ids or not spec_id.startswith("SPEC::")),
                "IDENTITY",
                "Specification exists",
                errors,
                validated_rules,
                soft=not bool(spec_ids),
                warnings=warnings,
                warning_message="Specification registry empty — category used as identity proxy",
            ),
            check(
                bool(decision.get("decision_id"))
                and bool(decision.get("decision_key"))
                and bool(object_id)
                and bool(intent_id)
                and bool(beam_id)
                and bool(context_id),
                "IDENTITY",
                "No missing identifiers",
                errors,
                validated_rules,
            ),
        ]
