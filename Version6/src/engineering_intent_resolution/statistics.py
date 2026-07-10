"""Statistics for engineering intent resolution."""

from __future__ import annotations

from typing import Any, Dict, List


class ResolutionStatistics:
    """Compute resolution KPIs and health metrics."""

    @staticmethod
    def build(
        intent_objects: List[dict[str, Any]],
        decisions: List[dict[str, Any]],
        merges: List[dict[str, Any]],
        conflicts: List[dict[str, Any]],
        graphs: List[dict[str, Any]],
    ) -> dict[str, Any]:
        suppressed_count = sum(int(item.get("suppressed_intent_count") or 0) for item in decisions)
        categories: Dict[str, int] = {}
        for decision in decisions:
            category = str(decision.get("decision_category") or "UNKNOWN")
            categories[category] = categories.get(category, 0) + 1

        intent_count = len(intent_objects)
        decision_count = len(decisions)
        reduction_ratio = (
            round(1.0 - (decision_count / intent_count), 4) if intent_count else 0.0
        )
        decision_efficiency = (
            round(decision_count / intent_count, 4) if intent_count else 0.0
        )
        resolved_conflicts = sum(1 for item in conflicts if item.get("resolved"))
        covered_intents = set()
        for decision in decisions:
            primary = decision.get("primary_intent") or {}
            if primary.get("intent_id"):
                covered_intents.add(str(primary.get("intent_id")))
            for item in decision.get("supporting_intents") or []:
                if item.get("intent_id"):
                    covered_intents.add(str(item.get("intent_id")))
            for item in decision.get("suppressed_intents") or []:
                if item.get("intent_id"):
                    covered_intents.add(str(item.get("intent_id")))

        coverage = round((len(covered_intents) / intent_count) * 100, 2) if intent_count else 100.0
        avg_confidence = (
            round(
                sum(float(item.get("decision_confidence") or 0.0) for item in decisions) / decision_count,
                2,
            )
            if decision_count
            else 100.0
        )

        return {
            "intent_objects": intent_count,
            "engineering_decisions": decision_count,
            "merged_intent": len(merges),
            "suppressed_intent": suppressed_count,
            "conflict_count": len(conflicts),
            "resolved_conflicts": resolved_conflicts,
            "decision_categories": categories,
            "decision_coverage_percent": coverage,
            "intent_reduction_ratio": reduction_ratio,
            "decision_efficiency": decision_efficiency,
            "engineering_confidence": avg_confidence,
            "graph_count": len(graphs),
            "eligible_decisions": sum(
                1 for item in decisions if item.get("production_eligibility") == "ELIGIBLE"
            ),
        }

    @staticmethod
    def build_health(statistics: dict[str, Any]) -> dict[str, Any]:
        coverage = float(statistics.get("decision_coverage_percent") or 0.0)
        conflicts = int(statistics.get("conflict_count") or 0)
        resolved = int(statistics.get("resolved_conflicts") or 0)
        confidence = float(statistics.get("engineering_confidence") or 0.0)
        health = "HEALTHY"
        if coverage < 100.0 or resolved < conflicts:
            health = "ATTENTION"
        if coverage < 90.0:
            health = "DEGRADED"
        return {
            "engineering_resolution_health": health,
            "decision_coverage_percent": coverage,
            "engineering_confidence": confidence,
            "conflict_resolution_rate": (
                round((resolved / conflicts) * 100, 2) if conflicts else 100.0
            ),
            "intent_reduction_ratio": statistics.get("intent_reduction_ratio", 0.0),
            "decision_efficiency": statistics.get("decision_efficiency", 0.0),
        }

    @staticmethod
    def build_summary(
        statistics: dict[str, Any],
        health: dict[str, Any],
        validation_status: str,
    ) -> dict[str, Any]:
        return {
            "intent_objects": statistics.get("intent_objects", 0),
            "engineering_decisions": statistics.get("engineering_decisions", 0),
            "merged_intent": statistics.get("merged_intent", 0),
            "suppressed_intent": statistics.get("suppressed_intent", 0),
            "conflict_count": statistics.get("conflict_count", 0),
            "resolved_conflicts": statistics.get("resolved_conflicts", 0),
            "decision_categories": statistics.get("decision_categories", {}),
            "decision_coverage_percent": statistics.get("decision_coverage_percent", 0.0),
            "intent_reduction_ratio": statistics.get("intent_reduction_ratio", 0.0),
            "decision_efficiency": statistics.get("decision_efficiency", 0.0),
            "engineering_confidence": statistics.get("engineering_confidence", 0.0),
            "engineering_resolution_health": health.get("engineering_resolution_health"),
            "validation_status": validation_status,
        }
