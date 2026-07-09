"""Expansion recovery statistics and health metrics."""

from __future__ import annotations

from typing import Any, Dict, List


class ExpansionStatistics:
    """Compute expansion coverage and recovery metrics."""

    @staticmethod
    def build(
        candidates: List[dict[str, Any]],
        decisions: List[dict[str, Any]],
        recovered_objects: List[dict[str, Any]],
        snapshot: dict[str, Any],
        *,
        registry_count: int = 0,
    ) -> dict[str, Any]:
        inventory_count = len(snapshot.get("inventory") or [])
        existing_bar_count = len(snapshot.get("existing_bars") or [])
        approved = [item for item in decisions if item.get("recover")]
        rejected = [item for item in decisions if not item.get("recover")]
        recovered = registry_count or len(recovered_objects)
        new_recoveries = len(approved)

        coverage_before = ExpansionStatistics._coverage(existing_bar_count, inventory_count)
        coverage_after_bars = existing_bar_count + new_recoveries
        coverage_after = ExpansionStatistics._coverage(coverage_after_bars, inventory_count)

        return {
            "objects_evaluated": len(candidates),
            "expansion_candidates": len(candidates),
            "recovered": recovered,
            "rejected": len(rejected),
            "approved": len(approved),
            "coverage_before_percent": coverage_before,
            "coverage_after_percent": coverage_after,
            "coverage_before_bars": existing_bar_count,
            "coverage_after_bars": coverage_after_bars,
            "inventory_count": inventory_count,
            "recovery_improvement_percent": round(coverage_after - coverage_before, 2),
            "expansion_classes": ExpansionStatistics._count_by(decisions, "expansion_class"),
            "decisions": ExpansionStatistics._count_by(decisions, "decision"),
        }

    @staticmethod
    def build_health(statistics: dict[str, Any]) -> dict[str, Any]:
        evaluated = max(statistics.get("objects_evaluated", 1), 1)
        recovered = statistics.get("recovered", 0)
        approved = max(statistics.get("approved", 0), 1)
        recovery_rate = round((recovered / approved) * 100, 2) if recovered else 0.0
        candidate_success = round((statistics.get("approved", 0) / evaluated) * 100, 2)
        coverage_gain = statistics.get("recovery_improvement_percent", 0.0)
        overall = round((recovery_rate * 0.4) + (candidate_success * 0.3) + (coverage_gain * 0.3), 2)
        return {
            "expansion_recovery_rate": recovery_rate,
            "candidate_success_rate": candidate_success,
            "coverage_gain_percent": coverage_gain,
            "overall_expansion_health": min(100.0, overall),
        }

    @staticmethod
    def build_summary(statistics: dict[str, Any], health: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
        return {
            **statistics,
            "validation_status": validation.get("status"),
            "expansion_health": health,
            "integration_success_percent": round(
                (validation.get("summary", {}).get("passed", 0) / max(validation.get("summary", {}).get("total_checks", 1), 1))
                * 100,
                2,
            ),
        }

    @staticmethod
    def _coverage(bar_count: int, inventory_count: int) -> float:
        if inventory_count <= 0:
            return 0.0
        return round((bar_count / inventory_count) * 100, 2)

    @staticmethod
    def _count_by(records: List[dict[str, Any]], key: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for record in records:
            value = str(record.get(key) or "UNKNOWN")
            counts[value] = counts.get(value, 0) + 1
        return counts
