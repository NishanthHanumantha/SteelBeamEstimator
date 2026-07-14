"""Confidence reporting extensions — Phase G.5.3.3."""

from __future__ import annotations

from typing import Any, Dict, List

from src.property_resolver.property_resolver_types import RESOLUTION_CONFLICT


class PropertyResolutionConfidenceReporting:
    """Build confidence-focused reporting artifacts."""

    @staticmethod
    def build(resolved_properties: List[dict[str, Any]]) -> dict[str, Any]:
        if not resolved_properties:
            return {
                "average_confidence_by_strategy": {},
                "highest_confidence_objects": [],
                "lowest_confidence_objects": [],
                "conflict_confidence_distribution": {},
                "top_uncertain_engineering_properties": [],
                "confidence_percentiles": {},
            }

        by_strategy: Dict[str, List[float]] = {}
        ranked: List[dict[str, Any]] = []

        for resolved in resolved_properties:
            strategy = str(resolved.get("resolution_strategy", "UNKNOWN"))
            confidence = float(resolved.get("resolution_confidence", 0.0))
            by_strategy.setdefault(strategy, []).append(confidence)
            ranked.append(
                {
                    "resolved_property_id": resolved.get("resolved_property_id"),
                    "engineering_object_id": resolved.get("engineering_object_id"),
                    "property_type": resolved.get("property_type"),
                    "resolution_strategy": strategy,
                    "resolution_confidence": confidence,
                    "resolved_value": resolved.get("resolved_value"),
                }
            )

        ranked.sort(key=lambda item: item["resolution_confidence"], reverse=True)
        confidences = sorted(float(item["resolution_confidence"]) for item in ranked)

        conflict_confidences = by_strategy.get(RESOLUTION_CONFLICT, [])
        conflict_distribution = PropertyResolutionConfidenceReporting._histogram(
            conflict_confidences
        )

        uncertain = sorted(
            ranked,
            key=lambda item: (
                item["resolution_confidence"],
                item["property_type"],
                item["engineering_object_id"],
            ),
        )[:10]

        return {
            "average_confidence_by_strategy": {
                strategy: round(sum(values) / len(values), 4)
                for strategy, values in sorted(by_strategy.items())
            },
            "highest_confidence_objects": ranked[:10],
            "lowest_confidence_objects": list(reversed(ranked[-10:])),
            "conflict_confidence_distribution": conflict_distribution,
            "top_uncertain_engineering_properties": uncertain,
            "confidence_percentiles": PropertyResolutionConfidenceReporting._percentiles(
                confidences
            ),
        }

    @staticmethod
    def _percentiles(confidences: List[float]) -> dict[str, float]:
        if not confidences:
            return {"p25": 0.0, "p50": 0.0, "p75": 0.0, "p90": 0.0}

        def percentile(values: List[float], pct: float) -> float:
            if len(values) == 1:
                return round(values[0], 4)
            index = (len(values) - 1) * pct
            lower = int(index)
            upper = min(lower + 1, len(values) - 1)
            weight = index - lower
            value = values[lower] * (1.0 - weight) + values[upper] * weight
            return round(value, 4)

        return {
            "p25": percentile(confidences, 0.25),
            "p50": percentile(confidences, 0.50),
            "p75": percentile(confidences, 0.75),
            "p90": percentile(confidences, 0.90),
        }

    @staticmethod
    def _histogram(confidences: List[float]) -> dict[str, int]:
        bins = [
            ("0.0-0.2", 0.0, 0.2),
            ("0.2-0.4", 0.2, 0.4),
            ("0.4-0.6", 0.4, 0.6),
            ("0.6-0.8", 0.6, 0.8),
            ("0.8-1.0", 0.8, 1.01),
        ]
        counts = {label: 0 for label, _, _ in bins}
        for confidence in confidences:
            for label, low, high in bins:
                if low <= confidence < high:
                    counts[label] += 1
                    break
        return counts
