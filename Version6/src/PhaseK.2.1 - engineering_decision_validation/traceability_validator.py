"""GROUP 2 — Traceability validation."""

from __future__ import annotations

from typing import Any, List

from _rule_helpers import check, require


class TraceabilityValidator:
    """Validate lineage references without mutating decisions."""

    def validate(
        self,
        decision: dict[str, Any],
        snapshot: dict[str, Any],
        errors: List[dict[str, str]],
        warnings: List[dict[str, str]],
        validated_rules: List[dict[str, str]],
        *,
        fail_on_broken: bool = True,
    ) -> List[bool]:
        indexes = snapshot.get("indexes") or {}
        evidence = decision.get("evidence") or {}
        primary = decision.get("primary_intent") or {}
        decision_id = str(decision.get("decision_id") or "")
        object_id = str(decision.get("engineering_object_id") or "")
        intent_id = str(primary.get("intent_id") or evidence.get("primary_intent_id") or "")
        context_id = str(evidence.get("calculation_context_id") or "")
        beam_id = str(decision.get("beam_id") or "")
        graph_id = str(decision.get("graph_id") or evidence.get("graph_id") or "")
        recovery_id = str(evidence.get("recovery_id") or decision.get("recovery_id") or "")
        soft = not fail_on_broken

        object_ok = (not (indexes.get("engineering_object_ids") or set())) or (
            object_id in (indexes.get("engineering_object_ids") or set())
        )
        intent_ok = (not (indexes.get("intent_ids") or set())) or (
            intent_id in (indexes.get("intent_ids") or set())
        )
        context_ok = (not (indexes.get("context_ids") or set())) or (
            context_id in (indexes.get("context_ids") or set())
        )
        beam_ok = (not (indexes.get("beam_ids") or set())) or (
            beam_id in (indexes.get("beam_ids") or set())
        )
        graph_ok = (not graph_id) or (not (indexes.get("graph_ids") or set())) or (
            graph_id in (indexes.get("graph_ids") or set())
        )
        recovery_ok = (not recovery_id) or (not (indexes.get("recovery_ids") or set())) or (
            recovery_id in (indexes.get("recovery_ids") or set())
        )
        decision_ok = decision_id in (indexes.get("decision_ids") or {decision_id})
        trace = (indexes.get("trace_by_decision") or {}).get(decision_id)

        return [
            check(
                bool(object_id) and object_ok,
                "TRACEABILITY",
                "Engineering Object reference valid",
                errors,
                validated_rules,
                soft=soft and not object_ok,
                warnings=warnings,
            ),
            check(
                bool(intent_id) and intent_ok,
                "TRACEABILITY",
                "Intent reference valid",
                errors,
                validated_rules,
                soft=soft and not intent_ok,
                warnings=warnings,
            ),
            check(
                decision_ok,
                "TRACEABILITY",
                "Decision reference valid",
                errors,
                validated_rules,
            ),
            check(
                recovery_ok,
                "TRACEABILITY",
                "Recovery reference valid",
                errors,
                validated_rules,
                soft=True,
                warnings=warnings,
                warning_message="Recovery reference not applicable or not indexed",
            ),
            check(
                bool(beam_id) and beam_ok,
                "TRACEABILITY",
                "Beam reference valid",
                errors,
                validated_rules,
            ),
            check(
                bool(context_id) and context_ok,
                "TRACEABILITY",
                "Calculation Context valid",
                errors,
                validated_rules,
            ),
            check(
                graph_ok,
                "TRACEABILITY",
                "Graph references valid",
                errors,
                validated_rules,
                soft=True,
                warnings=warnings,
                warning_message="Graph ID not found in exported graph set",
            ),
            check(
                bool(trace) or bool(evidence),
                "TRACEABILITY",
                "No broken lineage",
                errors,
                validated_rules,
            ),
            require(
                decision.get("source_bar_id"),
                "TRACEABILITY",
                "Source annotation reference present",
                errors,
                validated_rules,
            ),
        ]
