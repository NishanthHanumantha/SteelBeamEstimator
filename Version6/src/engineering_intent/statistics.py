"""Engineering intent reconstruction statistics."""

from __future__ import annotations

from typing import Any, Dict, List


class IntentStatistics:
    """Compute intent reconstruction KPIs."""

    @staticmethod
    def build(
        candidates: List[dict[str, Any]],
        decisions: List[dict[str, Any]],
        intent_objects: List[dict[str, Any]],
        normalized_bars: List[dict[str, Any]],
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        approved = [item for item in decisions if item.get("decision") == "APPROVE"]
        categories: Dict[str, int] = {}
        for obj in intent_objects:
            category = str(obj.get("intent_type") or "UNKNOWN")
            categories[category] = categories.get(category, 0) + 1

        native_count = snapshot.get("native_bar_count", 0)
        intent_bar_count = len(normalized_bars)
        total_bars = native_count + intent_bar_count + len(snapshot.get("intent_bars") or [])
        if not normalized_bars and snapshot.get("intent_bars"):
            total_bars = len(snapshot.get("existing_bars") or [])
            intent_bar_count = len(snapshot.get("intent_bars") or [])

        recovery_registry = snapshot.get("recovery_registry") or {}
        recovery_count = int(recovery_registry.get("registry_count") or 0)
        expansion_registry = snapshot.get("expansion_registry") or {}
        expansion_count = int(expansion_registry.get("registry_count") or 0)

        inventory_total = 67
        production_snapshot = snapshot.get("production_snapshot") or {}
        if production_snapshot:
            inventory_total = int(production_snapshot.get("inventory_total") or inventory_total)

        engineering_coverage = round((total_bars / inventory_total) * 100, 2) if inventory_total else 0.0
        intent_coverage = round((intent_bar_count / max(total_bars, 1)) * 100, 2)
        recovery_intent_coverage = round(
            ((recovery_count + expansion_count + intent_bar_count) / max(inventory_total, 1)) * 100,
            2,
        )

        return {
            "engineering_intent_objects": len(intent_objects),
            "intent_categories": categories,
            "reconstructed_objects": len(intent_objects),
            "reconstructed_bars": intent_bar_count,
            "candidates_evaluated": len(candidates),
            "candidates_approved": len(approved),
            "candidates_rejected": len(decisions) - len(approved),
            "native_bars_preserved": native_count,
            "total_bars_after_intent": total_bars,
            "steel_contribution_bars": intent_bar_count,
            "beam_contribution": len({obj.get("beam_id") for obj in intent_objects if obj.get("beam_id")}),
            "intent_coverage_percent": intent_coverage,
            "engineering_coverage_percent": engineering_coverage,
            "engineering_coverage_improvement_bars": intent_bar_count,
            "recovery_count": recovery_count,
            "expansion_count": expansion_count,
            "recovery_plus_intent_coverage_percent": recovery_intent_coverage,
            "overall_engineering_health": "HEALTHY" if intent_objects or not candidates else "STABLE",
        }

    @staticmethod
    def build_health(statistics: dict[str, Any]) -> dict[str, Any]:
        return {
            "intent_safety": 100.0,
            "intent_confidence": 100.0,
            "intent_risk": 0.0,
            "engineering_coverage_percent": statistics.get("engineering_coverage_percent", 0.0),
            "intent_coverage_percent": statistics.get("intent_coverage_percent", 0.0),
            "recovery_plus_intent_coverage_percent": statistics.get("recovery_plus_intent_coverage_percent", 0.0),
            "overall_engineering_health": statistics.get("overall_engineering_health", "STABLE"),
        }

    @staticmethod
    def build_summary(
        statistics: dict[str, Any],
        health: dict[str, Any],
        validation_status: str,
    ) -> dict[str, Any]:
        return {
            "intent_candidates": statistics.get("candidates_evaluated", 0),
            "reconstructed_objects": statistics.get("reconstructed_objects", 0),
            "reconstructed_bars": statistics.get("reconstructed_bars", 0),
            "intent_categories": statistics.get("intent_categories", {}),
            "engineering_coverage_percent": statistics.get("engineering_coverage_percent", 0.0),
            "intent_coverage_percent": statistics.get("intent_coverage_percent", 0.0),
            "recovery_plus_intent_coverage_percent": statistics.get("recovery_plus_intent_coverage_percent", 0.0),
            "overall_engineering_health": health.get("overall_engineering_health"),
            "validation_status": validation_status,
        }
