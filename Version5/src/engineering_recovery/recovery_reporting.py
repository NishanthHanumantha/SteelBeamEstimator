"""Recovery health metrics and summary reporting."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


class RecoveryReporting:
    """Compute recovery statistics and summary."""

    def build_statistics(
        self,
        candidates: List[dict[str, Any]],
        decisions: List[dict[str, Any]],
        recovered_objects: List[dict[str, Any]],
        rejected_decisions: List[dict[str, Any]],
        normalized_bars: List[dict[str, Any]],
        existing_bar_count: int,
    ) -> dict[str, Any]:
        approved = [item for item in decisions if item.get("recover")]
        categories = Counter(str(item.get("inventory", {}).get("category") or "Unknown") for item in approved)
        beams = Counter(str(item.get("beam_id") or "Unknown") for item in approved)
        avg_confidence = round(
            sum(float(item.get("confidence_score") or 0.0) for item in approved) / max(len(approved), 1),
            2,
        )
        success_count = sum(1 for bar in normalized_bars if bar.get("status") == "NORMALIZED")
        return {
            "recovery_candidates": len(candidates),
            "approved_candidates": len(approved),
            "rejected_candidates": len(rejected_decisions),
            "recovered_objects": len(recovered_objects),
            "recovered_normalized_bars": len(normalized_bars),
            "recovery_success_count": success_count,
            "recovery_success_percent": round((success_count / max(len(approved), 1)) * 100, 2),
            "recovery_confidence": avg_confidence,
            "recovered_beams": dict(sorted(beams.items())),
            "recovered_categories": dict(sorted(categories.items())),
        }

    def build_health(
        self,
        statistics: dict[str, Any],
        steel_coverage_before: float,
        steel_coverage_after: float,
    ) -> dict[str, Any]:
        approved = statistics.get("approved_candidates", 0)
        recovered = statistics.get("recovered_objects", 0)
        recovery_success = statistics.get("recovery_success_percent", 0.0)
        recovery_confidence = statistics.get("recovery_confidence", 0.0)
        recovery_safety = round(
            min(
                100.0,
                (recovery_success * 0.5) + (recovery_confidence * 0.3) + (100.0 if recovered <= approved else 0.0) * 0.2,
            ),
            2,
        )
        recovery_risk = round(max(0.0, 100.0 - recovery_safety), 2)
        return {
            "recovery_safety": recovery_safety,
            "recovery_confidence": recovery_confidence,
            "recovery_risk": recovery_risk,
            "steel_coverage_before_percent": steel_coverage_before,
            "steel_coverage_after_percent": steel_coverage_after,
            "steel_coverage_improvement_percent": round(steel_coverage_after - steel_coverage_before, 2),
            "approved_recovery_scope": approved,
            "actual_recovered_objects": recovered,
        }

    def build_summary(
        self,
        statistics: dict[str, Any],
        health: dict[str, Any],
        rejected_decisions: List[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "recovery_candidates": statistics.get("recovery_candidates", 0),
            "recovered_objects": statistics.get("recovered_objects", 0),
            "rejected_recovery_candidates": statistics.get("rejected_candidates", 0),
            "recovery_success_percent": statistics.get("recovery_success_percent", 0.0),
            "recovered_beams": statistics.get("recovered_beams", {}),
            "recovered_categories": statistics.get("recovered_categories", {}),
            "recovered_normalized_bars": statistics.get("recovered_normalized_bars", 0),
            "recovery_safety": health.get("recovery_safety", 0.0),
            "recovery_confidence": health.get("recovery_confidence", 0.0),
            "recovery_risk": health.get("recovery_risk", 0.0),
            "steel_coverage_before_percent": health.get("steel_coverage_before_percent", 0.0),
            "steel_coverage_after_percent": health.get("steel_coverage_after_percent", 0.0),
            "steel_coverage_improvement_percent": health.get("steel_coverage_improvement_percent", 0.0),
            "top_rejection_reasons": self._top_rejection_reasons(rejected_decisions),
        }

    @staticmethod
    def _top_rejection_reasons(rejected_decisions: List[dict[str, Any]], limit: int = 5) -> List[dict[str, Any]]:
        counter: Counter[str] = Counter()
        for decision in rejected_decisions:
            for reason in decision.get("blocking_reasons") or []:
                counter[str(reason)] += 1
        return [{"reason": reason, "count": count} for reason, count in counter.most_common(limit)]

    @staticmethod
    def compute_steel_coverage(normalized_count: int, inventory_count: int) -> float:
        if inventory_count <= 0:
            return 0.0
        return round((normalized_count / inventory_count) * 100, 2)
