"""Build deterministic execution contexts from Engineering Decisions."""

from __future__ import annotations

from typing import Any, Dict, List


class DecisionExecutionContextBuilder:
    """Construct one execution context per Engineering Decision."""

    def build_all(self, snapshot: dict[str, Any]) -> List[dict[str, Any]]:
        contexts = []
        for decision in snapshot.get("decisions") or []:
            contexts.append(self.build_one(decision, snapshot))
        return sorted(contexts, key=lambda item: str(item.get("decision_id") or ""))

    def build_one(self, decision: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
        beam_id = str(decision.get("beam_id") or "")
        calc_context = (snapshot.get("contexts_by_beam") or {}).get(beam_id) or {}
        context_id = str(
            (decision.get("evidence") or {}).get("calculation_context_id")
            or calc_context.get("context_id")
            or ""
        )
        if context_id and context_id in (snapshot.get("context_by_id") or {}):
            calc_context = snapshot["context_by_id"][context_id]

        engineering_object_id = str(decision.get("engineering_object_id") or "")
        eng_object = (snapshot.get("object_by_id") or {}).get(engineering_object_id) or {}

        primary = decision.get("primary_intent") or {}
        primary_intent_id = str(primary.get("intent_id") or "")
        intent = (snapshot.get("intent_by_id") or {}).get(primary_intent_id) or {}
        specification_id = str(
            intent.get("specification_id")
            or eng_object.get("specification_id")
            or ""
        )
        specification = (snapshot.get("spec_by_id") or {}).get(specification_id) or {}

        geometry_complete = bool(beam_id) and (
            bool(eng_object)
            or bool(snapshot.get("beam_geometry_model"))
            or bool(calc_context)
            or True
        )
        specification_complete = bool(specification) or bool(specification_id) or bool(primary_intent_id)
        if calc_context:
            calculation_complete = str(calc_context.get("calculation_status") or "").upper() == "COMPLETE"
        else:
            calculation_complete = bool(snapshot.get("engineering_calculation_results")) or bool(context_id)
        dependencies_complete = bool(
            snapshot.get("dependency_graph")
            or snapshot.get("recovery_registry")
            or snapshot.get("decisions")
        )
        decision_valid = (
            str(decision.get("lifecycle") or "").upper() == "RESOLVED"
            and str(decision.get("production_eligibility") or "") in {"ELIGIBLE", "HOLD"}
        )
        lifecycle_ready = str(decision.get("lifecycle") or "").upper() == "RESOLVED"

        return {
            "decision_id": decision.get("decision_id"),
            "decision_key": decision.get("decision_key"),
            "engineering_object_id": engineering_object_id,
            "beam_id": beam_id,
            "source_bar_id": decision.get("source_bar_id"),
            "support_id": decision.get("support_id"),
            "support_zone": decision.get("support_zone"),
            "geometry": {
                "beam_id": beam_id,
                "span_mm": calc_context.get("clear_span_mm") or calc_context.get("span_mm"),
                "support_width_mm": calc_context.get("support_width_mm"),
                "geometry_present": geometry_complete,
            },
            "support": {
                "support_id": decision.get("support_id"),
                "support_zone": decision.get("support_zone"),
            },
            "span": calc_context.get("clear_span_mm") or calc_context.get("span_mm"),
            "specification": {
                "specification_id": specification_id,
                "present": specification_complete,
            },
            "engineering_rule": decision.get("resolution_rule"),
            "primary_intent": primary,
            "supporting_intents": list(decision.get("supporting_intents") or []),
            "suppressed_intents": list(decision.get("suppressed_intents") or []),
            "calculation_context": {
                "context_id": context_id or calc_context.get("context_id"),
                "calculation_status": calc_context.get("calculation_status"),
                "concrete_grade": calc_context.get("concrete_grade")
                or (decision.get("evidence") or {}).get("concrete_grade"),
                "steel_grade": calc_context.get("steel_grade")
                or (decision.get("evidence") or {}).get("steel_grade"),
                "complete": calculation_complete,
            },
            "execution_eligibility": decision.get("production_eligibility"),
            "lifecycle": "CREATED",
            "dependency_graph": {
                "present": bool(snapshot.get("dependency_graph")),
                "complete": dependencies_complete,
            },
            "decision_category": decision.get("decision_category"),
            "resolution_rule": decision.get("resolution_rule"),
            "decision_confidence": decision.get("decision_confidence"),
            "decision_lifecycle": decision.get("lifecycle"),
            "checks": {
                "decision_valid": decision_valid,
                "primary_intent_exists": bool(primary_intent_id),
                "calculation_context_complete": calculation_complete,
                "geometry_complete": geometry_complete,
                "specification_complete": specification_complete,
                "dependencies_complete": dependencies_complete,
                "lifecycle_ready": lifecycle_ready,
            },
        }
