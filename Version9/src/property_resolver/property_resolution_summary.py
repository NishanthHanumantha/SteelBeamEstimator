"""Property resolution summary — Phase G.5.3.2 / confidence G.5.3.3."""

from __future__ import annotations

import statistics
from typing import Any, Dict, List, Set

from src.property_resolver.property_availability import build_lifecycle_reporting
from src.property_resolver.property_resolution_confidence_reporting import (
    PropertyResolutionConfidenceReporting,
)
from src.property_resolver.property_resolver_types import (
    RESOLUTION_CONFLICT,
    RESOLUTION_UNKNOWN,
)


class PropertyResolutionSummary:
    """Build project-level property resolution summary."""

    @staticmethod
    def build(
        engineering_objects: List[dict[str, Any]],
        engineering_properties: List[dict[str, Any]],
        resolved_properties: List[dict[str, Any]],
        conflicts: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        by_strategy: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        confidences: List[float] = []
        strategy_confidences: Dict[str, List[float]] = {}
        candidate_counts: List[int] = []
        object_ids: Set[str] = set()

        for resolved in resolved_properties:
            strategy = str(resolved.get("resolution_strategy", "UNKNOWN"))
            confidence = float(resolved.get("resolution_confidence", 0.0))
            by_strategy[strategy] = by_strategy.get(strategy, 0) + 1
            strategy_confidences.setdefault(strategy, []).append(confidence)
            ptype = str(resolved.get("property_type", "UNKNOWN"))
            by_type[ptype] = by_type.get(ptype, 0) + 1
            confidences.append(confidence)
            candidate_counts.append(int(resolved.get("candidate_count", 0)))
            object_ids.add(str(resolved.get("engineering_object_id", "")))

        conflict_resolved = by_strategy.get(RESOLUTION_CONFLICT, 0)
        conflict_rate = (
            round(conflict_resolved / len(resolved_properties), 4)
            if resolved_properties
            else 0.0
        )
        avg_candidates = (
            round(sum(candidate_counts) / len(candidate_counts), 2)
            if candidate_counts
            else 0.0
        )
        confidence_histogram = PropertyResolutionSummary._histogram(confidences)
        confidence_reporting = PropertyResolutionConfidenceReporting.build(resolved_properties)
        lifecycle_reporting = build_lifecycle_reporting(resolved_properties)
        parsed_confidences = [
            float(resolved.get("resolution_confidence", 0.0))
            for resolved in resolved_properties
            if resolved.get("resolution_strategy") != RESOLUTION_UNKNOWN
        ]

        return {
            "phase": "Phase G.5.3.4",
            "status": "PROPERTIES_RESOLVED",
            "engineering_object_count": len(engineering_objects),
            "engineering_property_count": len(engineering_properties),
            "resolved_property_count": len(resolved_properties),
            "resolved_by_strategy": by_strategy,
            "resolved_by_type": by_type,
            "conflict_count": len(conflicts),
            "unresolved_conflict_count": conflict_resolved,
            "average_resolution_confidence": round(
                sum(confidences) / len(confidences) if confidences else 0.0, 4
            ),
            "average_parsed_resolution_confidence": round(
                sum(parsed_confidences) / len(parsed_confidences) if parsed_confidences else 0.0,
                4,
            ),
            "minimum_resolution_confidence": round(min(confidences), 4) if confidences else 0.0,
            "maximum_resolution_confidence": round(max(confidences), 4) if confidences else 0.0,
            "median_resolution_confidence": round(
                statistics.median(confidences) if confidences else 0.0, 4
            ),
            "confidence_histogram": confidence_histogram,
            "strategy_confidence_averages": {
                strategy: round(sum(values) / len(values), 4)
                for strategy, values in sorted(strategy_confidences.items())
            },
            "confidence_distribution": confidence_histogram,
            "conflict_rate": conflict_rate,
            "average_candidates_per_resolution": avg_candidates,
            "confidence_reporting": confidence_reporting,
            "lifecycle_distribution": lifecycle_reporting["lifecycle_summary"],
            "status_distribution": lifecycle_reporting["status_distribution"],
            "availability_distribution": lifecycle_reporting["availability_summary"],
            "lifecycle_reporting": lifecycle_reporting,
            "registry_counts": {
                "resolved_property_count": registry.get("resolved_property_count", 0),
                "engineering_property_count": registry.get("engineering_property_count", 0),
            },
            "validation_result": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
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
