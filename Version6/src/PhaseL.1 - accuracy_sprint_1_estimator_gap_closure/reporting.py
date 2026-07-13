"""Build report and dashboard payloads for Phase L.1."""

from __future__ import annotations

from typing import Any, Dict, List

from accuracy_loader import MODEL_VERSION, PHASE


class AccuracyReporting:
    """Assemble structured report, matrix and dashboard."""

    @staticmethod
    def build_report(result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "run_timestamp": result.get("run_timestamp"),
            "benchmark_project": "Sobha Galera Clubhouse",
            "statistics": result.get("statistics"),
            "health": result.get("health"),
            "summary": result.get("summary"),
            "validation_status": (result.get("validation") or {}).get("status"),
            "idempotent": result.get("idempotent"),
            "config": result.get("config"),
            "gap_count": len(result.get("classified_gaps") or []),
            "improvement_count": len((result.get("improvement_tracker") or {}).get("improvements") or []),
        }

    @staticmethod
    def build_gap_matrix(gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
        rows = []
        for g in gaps:
            rows.append({
                "gap_id": g.get("gap_id"),
                "gap_category": g.get("gap_category"),
                "priority": g.get("priority"),
                "priority_rank": g.get("priority_rank"),
                "title": g.get("title"),
                "affected_beams_count": len(g.get("affected_beams") or []),
                "affected_roles": ", ".join(g.get("affected_roles") or []),
                "steel_impact_kg": g.get("estimated_steel_impact_kg", 0.0),
                "future_phase": g.get("future_phase"),
                "root_cause_where": (g.get("root_cause") or {}).get("where_introduced"),
            })
        return {"row_count": len(rows), "rows": rows}

    @staticmethod
    def build_dashboard(
        statistics: Dict[str, Any],
        coverage: Dict[str, Any],
        gaps: List[Dict[str, Any]],
        comparison: Dict[str, Any],
    ) -> Dict[str, Any]:
        v5b = comparison.get("v5_baseline") or {}
        by_priority = {}
        for g in gaps:
            p = str(g.get("priority") or "MEDIUM")
            by_priority[p] = by_priority.get(p, 0) + 1
        return {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "title": "Version6 Accuracy Sprint 1 — Engineering Accuracy Dashboard",
            "benchmark_project": "Sobha Galera Clubhouse",
            "kpis": {
                "beam_coverage_percent": statistics.get("beam_coverage_percent"),
                "geometry_coverage_percent": statistics.get("geometry_coverage_percent"),
                "steel_coverage_percent": statistics.get("steel_coverage_percent"),
                "diameter_coverage_percent": statistics.get("diameter_coverage_percent"),
                "reinforcement_role_coverage_percent": statistics.get("reinforcement_role_coverage_percent"),
                "engineering_rule_coverage_percent": statistics.get("engineering_rule_coverage_percent"),
                "decision_coverage_percent": statistics.get("decision_coverage_percent"),
                "row_coverage_percent": statistics.get("row_coverage_percent"),
                "estimator_equivalence_percent": statistics.get("estimator_equivalence_percent"),
                "overall_estimator_accuracy_percent": statistics.get("overall_estimator_accuracy_percent"),
            },
            "gaps": {
                "total": statistics.get("total_gaps"),
                "by_priority": by_priority,
                "critical": by_priority.get("CRITICAL", 0),
                "high": by_priority.get("HIGH", 0),
                "medium": by_priority.get("MEDIUM", 0),
                "low": by_priority.get("LOW", 0),
            },
            "v5_baseline": v5b,
            "accuracy_health": (statistics.get("overall_estimator_accuracy_percent") or 0.0) >= 50,
            "pipeline_completeness_percent": statistics.get("pipeline_completeness_percent"),
        }
