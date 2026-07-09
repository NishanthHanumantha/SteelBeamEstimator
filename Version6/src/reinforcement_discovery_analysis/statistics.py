"""Parser health metrics and discovery summary statistics."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from src.reinforcement_discovery_analysis.discovery_collector import DISCOVERY_STATUSES, round_pct


class DiscoveryStatistics:
    """Compute parser health metrics and summary statistics."""

    def build_parser_health(
        self,
        inventory: List[dict[str, Any]],
        funnel: dict[str, Any],
        classification: dict[str, Any],
        association: dict[str, Any],
        normalization: dict[str, Any],
    ) -> dict[str, Any]:
        counts = funnel.get("stage_counts") or {}
        baseline = max(counts.get("drawing_callouts", 0), 1)
        metrics = {
            "detection_success_percent": round_pct(counts.get("detected", 0), baseline),
            "classification_success_percent": classification.get("classification_success_percent", 0.0),
            "association_success_percent": association.get("association_success_percent", 0.0),
            "normalization_success_percent": normalization.get("normalization_success_percent", 0.0),
            "calculation_success_percent": round_pct(counts.get("calculated", 0), baseline),
            "export_success_percent": round_pct(counts.get("written_to_excel", 0), baseline),
        }
        metric_values = list(metrics.values())
        metrics["overall_discovery_success_percent"] = round(
            sum(metric_values) / len(metric_values),
            2,
        ) if metric_values else 0.0
        metrics["method"] = "reinforcement_discovery_only"
        metrics["baseline_callouts"] = baseline
        metrics["stage_counts"] = counts
        return metrics

    def build_summary(
        self,
        inventory: List[dict[str, Any]],
        funnel: dict[str, Any],
        parser_health: dict[str, Any],
        gap_analysis: dict[str, Any],
        unsupported_patterns: dict[str, Any],
    ) -> dict[str, Any]:
        status_counts = Counter(item.get("current_status") for item in inventory)
        top_losses = [
            {
                "transition": transition.get("to_label"),
                "loss": transition.get("loss"),
                "loss_percent": transition.get("loss_percent"),
            }
            for transition in funnel.get("transitions") or []
            if transition.get("loss", 0) > 0
        ]
        top_losses.sort(key=lambda item: item["loss"], reverse=True)
        return {
            "total_annotations": len(inventory),
            "funnel_ending_count": funnel.get("stage_counts", {}).get("written_to_excel", 0),
            "parser_health": parser_health,
            "status_distribution": dict(status_counts),
            "top_discovery_losses": top_losses[:5],
            "top_gaps": (gap_analysis.get("gaps") or [])[:5],
            "unsupported_pattern_count": unsupported_patterns.get("pattern_count", 0),
            "valid_statuses": list(DISCOVERY_STATUSES),
        }

    def top_association_failures(self, association: dict[str, Any]) -> List[dict[str, Any]]:
        return association.get("causes") or []

    def top_normalization_failures(self, normalization: dict[str, Any]) -> List[dict[str, Any]]:
        return normalization.get("reasons") or []
