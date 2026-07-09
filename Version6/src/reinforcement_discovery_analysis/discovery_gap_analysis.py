"""Rank reinforcement discovery gaps."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from src.reinforcement_discovery_analysis.discovery_collector import round_pct


class DiscoveryGapAnalyzer:
    """Rank missing engineering opportunities from discovery losses."""

    IMPACT_RANK = {"Very High": 4, "High": 3, "Medium": 2, "Low": 1}

    PATTERN_IMPACT = {
        "Unsupported notation": "Very High",
        "Unknown notation": "Very High",
        "Unknown beam": "High",
        "Multiple candidate beams": "High",
        "Engineering bar not created": "High",
        "Missing specification": "Medium",
        "Unknown leader": "Medium",
        "Missing parser metadata": "Medium",
        "Unknown reinforcement type": "Low",
        "Unknown diameter": "Low",
        "Unknown spacing": "Low",
    }

    def analyze(
        self,
        inventory: List[dict[str, Any]],
        classification: dict[str, Any],
        association: dict[str, Any],
        normalization: dict[str, Any],
        funnel: dict[str, Any],
    ) -> dict[str, Any]:
        gaps: List[dict[str, Any]] = []
        total = max(len(inventory), 1)

        for pattern in classification.get("top_unknown_patterns") or []:
            gaps.append(
                {
                    "gap_type": "unsupported_notation",
                    "title": f"Unsupported notation: {pattern.get('pattern')}",
                    "pattern": pattern.get("pattern"),
                    "count": pattern.get("count", 0),
                    "estimated_impact": self.PATTERN_IMPACT.get("Unsupported notation", "Very High"),
                    "estimated_downstream_effect_percent": round_pct(pattern.get("count", 0), total),
                    "examples": pattern.get("examples", []),
                }
            )

        for cause in association.get("causes") or []:
            reason = str(cause.get("reason"))
            gaps.append(
                {
                    "gap_type": "beam_association_failure",
                    "title": reason,
                    "count": cause.get("count", 0),
                    "estimated_impact": self.PATTERN_IMPACT.get(reason, "High"),
                    "estimated_downstream_effect_percent": round_pct(cause.get("count", 0), total),
                    "examples": cause.get("examples", []),
                }
            )

        for reason_item in normalization.get("reasons") or []:
            reason = str(reason_item.get("reason"))
            gaps.append(
                {
                    "gap_type": "normalization_failure",
                    "title": reason,
                    "count": reason_item.get("count", 0),
                    "estimated_impact": self.PATTERN_IMPACT.get(reason, "Medium"),
                    "estimated_downstream_effect_percent": round_pct(reason_item.get("count", 0), total),
                    "examples": reason_item.get("examples", []),
                }
            )

        for transition in funnel.get("transitions") or []:
            if transition.get("loss", 0) <= 0:
                continue
            gaps.append(
                {
                    "gap_type": "discovery_transition_loss",
                    "title": f"Loss at {transition.get('to_label')}",
                    "count": transition.get("loss", 0),
                    "estimated_impact": "Medium",
                    "estimated_downstream_effect_percent": transition.get("loss_percent", 0),
                    "details": transition,
                }
            )

        ranked = sorted(
            gaps,
            key=lambda item: (
                self.IMPACT_RANK.get(str(item.get("estimated_impact")), 0),
                item.get("estimated_downstream_effect_percent", 0),
                item.get("count", 0),
            ),
            reverse=True,
        )
        return {"gaps": ranked, "total_gaps": len(ranked)}

    def build_unsupported_patterns(self, inventory: List[dict[str, Any]]) -> dict[str, Any]:
        patterns: Dict[str, dict[str, Any]] = {}
        for item in inventory:
            if item.get("classified"):
                continue
            text = str(item.get("original_text") or "")
            bucket = patterns.setdefault(
                text,
                {
                    "original_text": text,
                    "occurrences": 0,
                    "example_locations": [],
                    "reason": "Unsupported notation",
                    "priority": "High",
                },
            )
            bucket["occurrences"] += 1
            if len(bucket["example_locations"]) < 5:
                bucket["example_locations"].append(
                    {
                        "discovery_id": item.get("discovery_id"),
                        "beam": item.get("beam_association"),
                        "coordinates": item.get("coordinates"),
                    }
                )

        ranked = sorted(patterns.values(), key=lambda item: item["occurrences"], reverse=True)
        for index, item in enumerate(ranked, start=1):
            if item["occurrences"] >= 10:
                item["priority"] = "Very High"
            elif item["occurrences"] >= 5:
                item["priority"] = "High"
            elif item["occurrences"] >= 2:
                item["priority"] = "Medium"
            else:
                item["priority"] = "Low"
            item["rank"] = index
        return {"patterns": ranked, "pattern_count": len(ranked)}
