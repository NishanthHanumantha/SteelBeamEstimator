"""Phase L.1 accuracy sprint KPI statistics."""

from __future__ import annotations

from typing import Any, Dict, List


class AccuracyStatistics:
    """Compute KPIs from comparison, coverage and gap data."""

    def build(
        self,
        comparison: Dict[str, Any],
        coverage: Dict[str, Any],
        gaps: List[Dict[str, Any]],
        snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        summ = comparison.get("summary") or {}
        v5b = comparison.get("v5_baseline") or {}
        decisions = snapshot.get("decisions") or []

        # Gap distribution
        gap_by_cat: Dict[str, int] = {}
        gap_by_priority: Dict[str, int] = {}
        for g in gaps:
            gap_by_cat[str(g.get("gap_category") or "UNKNOWN")] = (
                gap_by_cat.get(str(g.get("gap_category") or "UNKNOWN"), 0) + 1
            )
            gap_by_priority[str(g.get("priority") or "MEDIUM")] = (
                gap_by_priority.get(str(g.get("priority") or "MEDIUM"), 0) + 1
            )

        return {
            # Beam Coverage
            "beam_coverage_percent": coverage.get("beam_coverage_percent", 0.0),
            # Geometry
            "geometry_coverage_percent": coverage.get("geometry_coverage_percent", 0.0),
            # Steel Weight
            "estimator_steel_kg": summ.get("estimator_total_steel_kg", 0.0),
            "model_steel_kg": summ.get("model_total_steel_kg", 0.0),
            "steel_gap_kg": summ.get("steel_gap_kg", 0.0),
            "steel_coverage_percent": coverage.get("steel_coverage_percent", 0.0),
            # Diameter
            "diameter_coverage_percent": coverage.get("diameter_coverage_percent", 0.0),
            # Reinforcement Role
            "reinforcement_role_coverage_percent": coverage.get("reinforcement_role_coverage_percent", 0.0),
            # Engineering Rule
            "engineering_rule_coverage_percent": 0.0,
            # Decision
            "decision_coverage_percent": coverage.get("decision_coverage_percent", 0.0),
            "total_decisions": len(decisions),
            # Calculation
            "row_coverage_percent": summ.get("row_coverage_percent", 0.0),
            # Steel BBS Excel
            "bbs_coverage_percent": coverage.get("bbs_coverage_percent", 0.0),
            "excel_coverage_percent": coverage.get("excel_coverage_percent", 0.0),
            # Estimator Equivalence
            "estimator_equivalence_percent": coverage.get("estimator_equivalence_percent", 0.0),
            "overall_engineering_accuracy_percent": coverage.get("steel_coverage_percent", 0.0),
            "overall_estimator_accuracy_percent": coverage.get("estimator_equivalence_percent", 0.0),
            # Gaps
            "total_gaps": len(gaps),
            "gaps_by_category": gap_by_cat,
            "gaps_by_priority": gap_by_priority,
            "critical_gaps": gap_by_priority.get("CRITICAL", 0),
            "high_gaps": gap_by_priority.get("HIGH", 0),
            "medium_gaps": gap_by_priority.get("MEDIUM", 0),
            "low_gaps": gap_by_priority.get("LOW", 0),
            # V5 Baseline
            "v5_baseline_steel_coverage_percent": v5b.get("steel_coverage_percent", 0.0),
            "v5_baseline_row_coverage_percent": v5b.get("row_coverage_percent", 0.0),
            "v5_baseline_steel_gap_kg": v5b.get("steel_gap_kg", 0.0),
            # Pipeline
            "pipeline_completeness_percent": coverage.get("pipeline_completeness_percent", 0.0),
        }

    @staticmethod
    def build_health(statistics: Dict[str, Any]) -> Dict[str, Any]:
        equiv = float(statistics.get("estimator_equivalence_percent") or 0.0)
        gaps_crit = int(statistics.get("critical_gaps") or 0)
        row_cov = float(statistics.get("row_coverage_percent") or 0.0)
        if equiv >= 90 and gaps_crit == 0:
            status = "HEALTHY"
        elif equiv >= 50 or row_cov >= 50:
            status = "ATTENTION"
        else:
            status = "CRITICAL"
        return {
            "overall_accuracy_health": status,
            "estimator_equivalence_percent": equiv,
            "critical_gaps": gaps_crit,
            "row_coverage_percent": row_cov,
            "assessment": (
                "Model has significant accuracy gaps — see improvement backlog" if status == "CRITICAL"
                else "Model accuracy improving — targeted improvements needed" if status == "ATTENTION"
                else "Model approaching estimator equivalence"
            ),
        }

    @staticmethod
    def build_summary(
        statistics: Dict[str, Any],
        health: Dict[str, Any],
        validation_status: str,
    ) -> Dict[str, Any]:
        return {
            "beam_coverage_percent": statistics.get("beam_coverage_percent"),
            "geometry_coverage_percent": statistics.get("geometry_coverage_percent"),
            "steel_coverage_percent": statistics.get("steel_coverage_percent"),
            "diameter_coverage_percent": statistics.get("diameter_coverage_percent"),
            "reinforcement_role_coverage_percent": statistics.get("reinforcement_role_coverage_percent"),
            "engineering_rule_coverage_percent": statistics.get("engineering_rule_coverage_percent"),
            "decision_coverage_percent": statistics.get("decision_coverage_percent"),
            "row_coverage_percent": statistics.get("row_coverage_percent"),
            "bbs_coverage_percent": statistics.get("bbs_coverage_percent"),
            "excel_coverage_percent": statistics.get("excel_coverage_percent"),
            "estimator_equivalence_percent": statistics.get("estimator_equivalence_percent"),
            "overall_engineering_accuracy_percent": statistics.get("overall_engineering_accuracy_percent"),
            "overall_estimator_accuracy_percent": statistics.get("overall_estimator_accuracy_percent"),
            "total_gaps": statistics.get("total_gaps"),
            "critical_gaps": statistics.get("critical_gaps"),
            "high_gaps": statistics.get("high_gaps"),
            "overall_accuracy_health": health.get("overall_accuracy_health"),
            "validation_status": validation_status,
        }
