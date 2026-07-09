"""Deterministic engineering recommendations from rejection analysis."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_object_audit.audit_collector import round_pct
from src.engineering_object_audit.rejection_statistics import IMPACT_BY_CODE


RECOMMENDATIONS = {
    "MISSING_SPECIFICATION": "Improve specification binding before engineering object creation.",
    "MISSING_GEOMETRY": "Resolve beam geometry and association before creating engineering objects.",
    "MISSING_POSITION": "Resolve reinforcement position context before engineering object creation.",
    "MISSING_BAR_ROLE": "Strengthen bar role inference during engineering object creation.",
    "MISSING_DIAMETER": "Ensure diameter parsing completes before engineering object creation.",
    "MISSING_QUANTITY": "Resolve bar quantity before engineering object creation.",
    "DUPLICATE_SUPPRESSED": "Review duplicate callout collapse rules to avoid suppressing unique reinforcement.",
    "ENGINEERING_RULE_CONFLICT": "Resolve conflicting engineering rules before object creation.",
    "NORMALIZATION_FAILED": "Inspect normalization prerequisites for partially created engineering objects.",
    "AMBIGUOUS_CALLOUT": "Clarify ambiguous callout interpretation before object creation.",
    "UNSUPPORTED_NOTATION": "Extend notation support before engineering object creation.",
    "BEAM_NOT_ASSOCIATED": "Improve beam association heuristics for reinforcement annotations.",
    "MULTIPLE_BEAM_CANDIDATES": "Disambiguate multi-beam association before object creation.",
    "UNKNOWN": "Investigate unknown engineering object creation failures with full trace review.",
}

STEEL_RECOVERY_IMPACT = {
    "Very High": "High",
    "High": "Medium",
    "Medium": "Low",
    "Low": "Low",
}


class RecommendationEngine:
    """Generate deterministic recommendations grouped by rejection code."""

    def build(
        self,
        rejection_statistics: dict[str, Any],
        audits: List[dict[str, Any]],
    ) -> dict[str, Any]:
        recommendations: List[dict[str, Any]] = []
        for item in rejection_statistics.get("primary_rejection_codes") or []:
            code = item.get("rejection_code")
            impact = item.get("engineering_impact") or IMPACT_BY_CODE.get(code, "Medium")
            recommendations.append(
                {
                    "root_cause": code,
                    "recommendation": RECOMMENDATIONS.get(code, RECOMMENDATIONS["UNKNOWN"]),
                    "expected_impact": impact,
                    "affected_callouts": item.get("count", 0),
                    "potential_steel_recovery": STEEL_RECOVERY_IMPACT.get(impact, "Low"),
                    "example_discovery_ids": self._examples(audits, code),
                }
            )
        recommendations.sort(
            key=lambda row: (
                {"Very High": 4, "High": 3, "Medium": 2, "Low": 1}.get(row["expected_impact"], 0),
                row["affected_callouts"],
            ),
            reverse=True,
        )
        return {"recommendations": recommendations}

    @staticmethod
    def _examples(audits: List[dict[str, Any]], code: str) -> List[str]:
        examples = []
        for audit in audits:
            if audit.get("primary_rejection_code") == code:
                examples.append(str(audit.get("discovery_id")))
            if len(examples) >= 5:
                break
        return examples

    def build_health(
        self,
        inventory_count: int,
        rejection_statistics: dict[str, Any],
        dependency_analysis: dict[str, Any],
        duplicate_analysis: dict[str, Any],
        readiness_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        accepted = rejection_statistics.get("accepted_count", 0)
        object_creation = round_pct(accepted, inventory_count)
        dependency_resolution = round_pct(
            inventory_count - sum(item.get("count", 0) for item in dependency_analysis.get("top_dependency_failures") or []),
            inventory_count,
        )
        specification_resolution = round_pct(
            inventory_count
            - sum(
                1
                for item in (dependency_analysis.get("records") or [])
                if not (item.get("components", {}).get("specification", {}).get("present"))
            ),
            inventory_count,
        )
        duplicate_resolution = round_pct(
            duplicate_analysis.get("valid_duplicate_groups", 0),
            max(duplicate_analysis.get("duplicate_group_count", 0), 1),
        )
        normalization_readiness = readiness_analysis.get("average_readiness_score", 0.0)
        subsystems = {
            "engineering_object_creation": object_creation,
            "dependency_resolution": dependency_resolution,
            "specification_resolution": specification_resolution,
            "duplicate_resolution": duplicate_resolution,
            "normalization_readiness": normalization_readiness,
        }
        overall = round(sum(subsystems.values()) / len(subsystems), 2)
        return {"subsystems": subsystems, "overall_object_creation_health": overall, "scale": "0-100"}
