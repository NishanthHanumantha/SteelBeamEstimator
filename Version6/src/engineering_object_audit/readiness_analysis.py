"""Compute engineering object readiness scores."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_object_audit.audit_collector import READINESS_COMPONENTS, round_pct


class ReadinessAnalyzer:
    """Compute readiness scores from dependency availability."""

    COMPONENT_WEIGHT = round(100 / len(READINESS_COMPONENTS), 2)

    def analyze_item(self, dependencies: dict[str, Any]) -> dict[str, Any]:
        components = dependencies.get("components") or {}
        scored: Dict[str, dict[str, Any]] = {}
        total = 0.0
        for name in READINESS_COMPONENTS:
            present = bool(components.get(name, {}).get("present"))
            score = self.COMPONENT_WEIGHT if present else 0.0
            scored[name] = {"present": present, "score": score}
            total += score
        first_missing = dependencies.get("first_missing_dependency")
        rejected_because = None
        if first_missing:
            rejected_because = f"{first_missing.replace('_', ' ').title()} missing"
        return {
            "discovery_id": dependencies.get("discovery_id"),
            "components": scored,
            "readiness_score": round(min(total, 100.0), 2),
            "rejected_because": rejected_because,
        }

    def analyze_all(
        self,
        inventory: List[dict[str, Any]],
        dependency_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        by_discovery = dependency_analysis.get("by_discovery_id") or {}
        records = []
        for item in inventory:
            dep = by_discovery.get(item.get("discovery_id"), {})
            records.append(self.analyze_item(dep))
        scores = [record["readiness_score"] for record in records]
        average = round(sum(scores) / len(scores), 2) if scores else 0.0
        return {
            "records": records,
            "by_discovery_id": {record["discovery_id"]: record for record in records},
            "average_readiness_score": average,
        }
