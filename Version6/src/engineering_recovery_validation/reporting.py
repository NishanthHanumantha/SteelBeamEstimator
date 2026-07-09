"""Recovery impact summary and report assembly."""

from __future__ import annotations

from typing import Any


class RecoveryImpactReporting:
    """Build executive summary for recovery impact validation."""

    def build_summary(
        self,
        pipeline_delta: dict[str, Any],
        recovery_effectiveness: dict[str, Any],
        qa_dashboard_impact: dict[str, Any],
        top_contributors: dict[str, Any],
        no_regression: dict[str, Any],
    ) -> dict[str, Any]:
        metrics = pipeline_delta.get("pipeline_delta") or {}
        normalization = qa_dashboard_impact.get("normalization_coverage") or {}

        return {
            "engineering_objects": metrics.get("engineering_objects"),
            "normalized_bars": metrics.get("normalized_bars"),
            "calculated_bars": metrics.get("calculated_bars"),
            "steel_weight_kg": metrics.get("steel_weight_kg"),
            "beam_schedule_rows": metrics.get("beam_schedule_rows"),
            "excel_rows": metrics.get("excel_rows"),
            "inventory_coverage_percent": metrics.get("inventory_coverage_percent"),
            "qa_dashboard_impact": {
                "normalization_coverage": normalization,
                "beam_coverage": qa_dashboard_impact.get("beam_coverage"),
                "schedule_coverage": qa_dashboard_impact.get("schedule_coverage"),
                "steel_quantity_coverage": qa_dashboard_impact.get("steel_quantity_coverage"),
                "highlights": qa_dashboard_impact.get("highlights") or [],
            },
            "recovery_roi": recovery_effectiveness.get("recovery_roi"),
            "contribution_score": recovery_effectiveness.get("contribution_score"),
            "engineering_value": recovery_effectiveness.get("engineering_value"),
            "top_contributors": {
                "recovery_candidates": [
                    {
                        "recovery_id": item.get("recovery_id"),
                        "discovery_id": item.get("discovery_id"),
                        "beam_id": item.get("beam_id"),
                        "engineering_contribution": item.get("engineering_contribution"),
                    }
                    for item in (top_contributors.get("top_recovery_candidates") or [])[:3]
                ],
                "beams": [
                    item.get("beam_id")
                    for item in (top_contributors.get("top_beams") or [])[:3]
                ],
            },
            "overall_engineering_improvement_percent": normalization.get("delta", 0.0),
            "no_regression_status": no_regression.get("status"),
            "append_only_growth": no_regression.get("append_only_growth"),
        }

    def build_report(
        self,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        summary = result.get("recovery_impact_summary") or {}
        return {
            "phase": result.get("phase"),
            "model_version": result.get("model_version"),
            "engine_version": result.get("engine_version"),
            "run_timestamp": result.get("run_timestamp"),
            "read_only_analysis": result.get("read_only_analysis"),
            "recovery_phase_validated": result.get("recovery_phase_validated"),
            "summary": summary,
            "recovery_effectiveness": result.get("recovery_effectiveness"),
            "no_regression": result.get("no_regression"),
            "validation_report": result.get("validation_report"),
            "export_paths": result.get("export_paths"),
        }
