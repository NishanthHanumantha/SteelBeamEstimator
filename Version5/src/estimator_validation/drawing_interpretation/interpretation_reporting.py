"""Interpretation audit reporting — Phase QA.3."""

from __future__ import annotations

from typing import Any, Dict, List


class InterpretationReporting:
    @staticmethod
    def build(result: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
        matching = result.get("interpretation_matching", {})
        entries = matching.get("entries", [])
        differences = [
            item
            for item in entries
            if item.get("classification")
            not in {
                "DRAWING_AND_ESTIMATOR_AND_PIPELINE",
                "DRAWING_AND_ESTIMATOR_ONLY",
                "DRAWING_AND_PIPELINE_ONLY",
            }
        ]
        differences.sort(key=lambda item: (-item.get("confidence", 0), item.get("beam_mark", "")))
        return {
            "phase": "Phase QA.3",
            "overall_interpretation_summary": summary,
            "per_beam_interpretation": InterpretationReporting._per_beam(entries),
            "per_role_interpretation": InterpretationReporting._per_role(entries),
            "per_engineering_concept": {
                "classification_distribution": matching.get("classification_distribution", {}),
                "concept_count": matching.get("entry_count", 0),
            },
            "per_length_interpretation": result.get("length_interpretation_report", {}),
            "estimator_manual_decisions": result.get("engineering_decisions", {}),
            "pipeline_missing_concepts": InterpretationReporting._filter_classification(
                entries, {"ESTIMATOR_ONLY", "DRAWING_AND_ESTIMATOR_ONLY"}
            ),
            "drawing_missing_concepts": InterpretationReporting._filter_classification(
                entries, {"ESTIMATOR_ONLY", "PIPELINE_ONLY"}
            ),
            "top_50_interpretation_differences": differences[:50],
            "recommended_engineering_changes": InterpretationReporting._recommended_changes(result),
            "confidence_statistics": InterpretationReporting._confidence_stats(entries),
            "root_cause_matrix": result.get("root_cause_matrix", {}),
        }

    @staticmethod
    def _per_beam(entries: List[dict[str, Any]]) -> Dict[str, dict[str, int]]:
        grouped: Dict[str, dict[str, int]] = {}
        for entry in entries:
            beam = entry.get("beam_mark", "UNKNOWN")
            grouped.setdefault(beam, {})
            classification = entry.get("classification", "UNKNOWN")
            grouped[beam][classification] = grouped[beam].get(classification, 0) + 1
        return grouped

    @staticmethod
    def _per_role(entries: List[dict[str, Any]]) -> Dict[str, dict[str, int]]:
        grouped: Dict[str, dict[str, int]] = {}
        for entry in entries:
            role = (entry.get("estimator") or entry.get("pipeline") or entry.get("drawing") or {}).get(
                "role", "UNKNOWN"
            )
            grouped.setdefault(role, {})
            classification = entry.get("classification", "UNKNOWN")
            grouped[role][classification] = grouped[role].get(classification, 0) + 1
        return grouped

    @staticmethod
    def _filter_classification(entries: List[dict[str, Any]], classifications: set[str]) -> List[dict[str, Any]]:
        return [item for item in entries if item.get("classification") in classifications]

    @staticmethod
    def _recommended_changes(result: dict[str, Any]) -> List[dict[str, Any]]:
        root_causes = result.get("interpretation_statistics", {}).get("root_cause_distribution", {})
        order = []
        priority = [
            ("Parser Interpretation", "Review drawing callout parsing and role assignment", "HIGH"),
            ("Identity", "Verify bar identity role/diameter mapping against drawing callouts", "HIGH"),
            ("Estimator Engineering Decision", "Validate manual estimator additions against drawing", "MEDIUM"),
            ("Beam Schedule", "Ensure schedule includes all drawing-derived roles", "HIGH"),
            ("Engineering Report", "Verify report schedule_table completeness", "MEDIUM"),
            ("Engineering Interpretation", "Align pipeline interpretation with drawing intent", "MEDIUM"),
            ("Drawing Ambiguity", "Resolve ambiguous drawing annotations", "MEDIUM"),
        ]
        for cause, fix, risk in priority:
            count = root_causes.get(cause, 0)
            if count:
                order.append(
                    {"root_cause": cause, "count": count, "recommended_change": fix, "estimated_risk": risk}
                )
        return order

    @staticmethod
    def _confidence_stats(entries: List[dict[str, Any]]) -> dict[str, Any]:
        buckets: Dict[str, int] = {"100": 0, "85": 0, "60": 0, "0": 0}
        for entry in entries:
            score = entry.get("confidence", 0)
            if score >= 100:
                buckets["100"] += 1
            elif score >= 85:
                buckets["85"] += 1
            elif score >= 60:
                buckets["60"] += 1
            else:
                buckets["0"] += 1
        return buckets
