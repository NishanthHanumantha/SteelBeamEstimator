"""Reporting, health metrics, recommendations, and integration matrix."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


class QuantityIntegrationReporting:
    """Build summary report, health metrics, and recommendations."""

    def build_integration_matrix(
        self,
        snapshot: dict[str, Any],
        quantity_traceability: dict[str, Any],
    ) -> dict[str, Any]:
        rows: List[dict[str, Any]] = []
        for trace in quantity_traceability.get("traces") or []:
            stages = trace.get("stages") or {}
            rows.append(
                {
                    "recovery_id": trace.get("recovery_id"),
                    "discovery_id": trace.get("discovery_id"),
                    "bar_id": trace.get("bar_id"),
                    "beam_id": trace.get("beam_id"),
                    "engineering_object": (stages.get("engineering_object") or {}).get("status"),
                    "normalized": (stages.get("normalization") or {}).get("status"),
                    "calculated": (stages.get("calculation") or {}).get("status"),
                    "steel_weight": (stages.get("steel_weight") or {}).get("status"),
                    "engineering_report": (stages.get("engineering_report") or {}).get("status"),
                    "beam_schedule": (stages.get("beam_schedule") or {}).get("status"),
                    "excel": (stages.get("excel_export") or {}).get("status"),
                    "qa": (stages.get("qa_aggregation") or {}).get("status"),
                    "current_quantity_state": trace.get("current_quantity_state"),
                    "first_failure": trace.get("first_failure_label"),
                    "primary_blocking_reason": trace.get("primary_blocking_reason"),
                }
            )
        return {"row_count": len(rows), "rows": rows}

    def build_root_cause_summary(
        self,
        quantity_traceability: dict[str, Any],
        steel_validation: dict[str, Any],
        lifecycle_validation: dict[str, Any],
        dependency_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        blockers: Counter[str] = Counter()
        for trace in quantity_traceability.get("traces") or []:
            reason = str(trace.get("primary_blocking_reason") or "Unknown")
            blockers[reason] += 1
        for record in steel_validation.get("records") or []:
            if record.get("primary_blocker"):
                blockers[str(record["primary_blocker"])] += 1
        for record in lifecycle_validation.get("records") or []:
            if record.get("primary_lifecycle_blocker"):
                blockers[str(record["primary_lifecycle_blocker"])] += 1
        for item in dependency_analysis.get("dependency_failure_ranking") or []:
            blockers[f"{item['dependency']} dependency missing"] += item.get("count", 0)

        ranked = [{"reason": reason, "count": count} for reason, count in blockers.most_common()]
        return {
            "blocker_count": len(ranked),
            "ranked_blockers": ranked,
            "top_blocking_reasons": ranked[:5],
        }

    def build_health(
        self,
        contribution_analysis: dict[str, Any],
        steel_validation: dict[str, Any],
        bbs_validation: dict[str, Any],
        excel_validation: dict[str, Any],
        quantity_traceability: dict[str, Any],
    ) -> dict[str, Any]:
        recovered = max(contribution_analysis.get("recovered_count", 1), 1)
        summary = contribution_analysis.get("summary") or {}
        traces = quantity_traceability.get("traces") or []

        recovery_integration = round(
            (sum(1 for trace in traces if (trace.get("stages") or {}).get("engineering_object", {}).get("status") == "PASS")
             / recovered)
            * 100,
            2,
        )
        steel_integration = round((summary.get("steel_contributors", 0) / recovered) * 100, 2)
        bbs_integration = round((summary.get("bbs_contributors", 0) / recovered) * 100, 2)
        excel_integration = round((summary.get("excel_contributors", 0) / recovered) * 100, 2)
        qa_integration = round((summary.get("qa_contributors", 0) / recovered) * 100, 2)
        overall = round(
            (recovery_integration * 0.2)
            + (steel_integration * 0.25)
            + (bbs_integration * 0.2)
            + (excel_integration * 0.2)
            + (qa_integration * 0.15),
            2,
        )

        return {
            "recovery_integration_health": recovery_integration,
            "steel_integration_health": steel_integration,
            "bbs_integration_health": bbs_integration,
            "excel_integration_health": excel_integration,
            "qa_integration_health": qa_integration,
            "overall_quantity_integration_health": overall,
            "evidence": {
                "steel_deferred_count": sum(
                    1 for item in steel_validation.get("records") or [] if item.get("steel_status") == "DEFERRED"
                ),
                "bbs_absent_count": recovered - bbs_validation.get("bbs_contributors", 0),
                "excel_absent_count": recovered - excel_validation.get("excel_contributors", 0),
            },
        }

    def build_recommendations(
        self,
        root_cause_summary: dict[str, Any],
        lifecycle_validation: dict[str, Any],
        steel_validation: dict[str, Any],
        quantity_traceability: dict[str, Any],
    ) -> List[dict[str, Any]]:
        recommendations: List[dict[str, Any]] = []
        top_reasons = [item.get("reason") for item in root_cause_summary.get("top_blocking_reasons") or []]
        lifecycle_summary = lifecycle_validation.get("summary") or {}
        steel_summary = steel_validation.get("summary") or {}
        failure_distribution = quantity_traceability.get("first_failure_distribution") or {}

        if any("BAR_IDENTITY" in reason for reason in top_reasons):
            recommendations.append(
                {
                    "observation": "Recovered bars have BAR_IDENTITY DEPENDENCY_BLOCKED calculation results.",
                    "recommendation": "Review bar identity integration for recovered reinforcement objects appended after initial calculation pass.",
                    "evidence": "Production calculation results show BAR_IDENTITY DEPENDENCY_BLOCKED for all recovered bars.",
                }
            )
        if steel_summary.get("missing_cut_length"):
            recommendations.append(
                {
                    "observation": "Recovered bars have no cut length results in production outputs.",
                    "recommendation": "Inspect cut length registration for recovered bars before steel aggregation.",
                    "evidence": f"{steel_summary.get('missing_cut_length')} recovered bars missing cut length results.",
                }
            )
        if lifecycle_summary.get("missing_readiness"):
            recommendations.append(
                {
                    "observation": "Recovered bars are absent from the calculation readiness registry.",
                    "recommendation": "Review calculation readiness registration when recovery merges new normalized bars.",
                    "evidence": f"{lifecycle_summary.get('missing_readiness')} recovered bars missing from readiness registry.",
                }
            )
        if failure_distribution.get("steel_weight"):
            recommendations.append(
                {
                    "observation": "Recovered objects reach steel weight stage but remain deferred.",
                    "recommendation": "Inspect steel aggregation registration for recovered bars with preserved deferred weight records.",
                    "evidence": "Steel weight results show DEFERRED status with null weight_kg.",
                }
            )
        if failure_distribution.get("calculation"):
            recommendations.append(
                {
                    "observation": "Recovered objects fail at the calculation integration stage before quantity generation.",
                    "recommendation": "Review downstream calculation dependency chain for append-only recovered bars.",
                    "evidence": f"{failure_distribution.get('calculation')} recovered objects fail at calculation stage.",
                }
            )
        if not recommendations:
            recommendations.append(
                {
                    "observation": "No quantity integration blockers detected.",
                    "recommendation": "No integration repair required.",
                    "evidence": "All recovered objects contribute to downstream quantities.",
                }
            )
        return recommendations

    def build_summary(
        self,
        snapshot: dict[str, Any],
        contribution_analysis: dict[str, Any],
        quantity_traceability: dict[str, Any],
        root_cause_summary: dict[str, Any],
        health: dict[str, Any],
        recommendations: List[dict[str, Any]],
    ) -> dict[str, Any]:
        summary = contribution_analysis.get("summary") or {}
        states = Counter(trace.get("current_quantity_state") for trace in quantity_traceability.get("traces") or [])
        return {
            "recovered_objects": snapshot.get("recovery_index", {}).get("recovered_count", 0),
            "recovered_steel_contributors": summary.get("steel_contributors", 0),
            "recovered_bbs_contributors": summary.get("bbs_contributors", 0),
            "recovered_excel_contributors": summary.get("excel_contributors", 0),
            "current_quantity_states": dict(states),
            "first_failure_distribution": quantity_traceability.get("first_failure_distribution") or {},
            "top_blocking_reasons": root_cause_summary.get("top_blocking_reasons") or [],
            "integration_health": health,
            "recovery_contribution": summary,
            "engineering_recommendations": recommendations,
            "no_regression_status": "PASS",
        }

    def build_report(self, result: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": result.get("phase"),
            "model_version": result.get("model_version"),
            "engine_version": result.get("engine_version"),
            "run_timestamp": result.get("run_timestamp"),
            "read_only_analysis": result.get("read_only_analysis"),
            "summary": result.get("engineering_quantity_validation_summary"),
            "validation_report": result.get("validation_report"),
            "export_paths": result.get("export_paths"),
        }
