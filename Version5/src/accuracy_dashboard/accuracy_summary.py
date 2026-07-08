"""Accuracy dashboard summary — Phase QA.ACCURACY.1."""

from __future__ import annotations

from typing import Any


class AccuracySummary:
    @staticmethod
    def build(result: dict[str, Any]) -> dict[str, Any]:
        excel = result.get("excel_accuracy", {})
        steel = result.get("steel_accuracy", {})
        return {
            "phase": result.get("phase"),
            "terminology_refinement": result.get("terminology_refinement"),
            "dashboard_version": result.get("dashboard_version"),
            "model_version": result.get("model_version"),
            "generated_workbook": result.get("generated_workbook"),
            "estimator_workbook": result.get("estimator_workbook"),
            "beam_coverage_percent": excel.get("beam_coverage_percent", 0.0),
            "schedule_coverage_percent": excel.get("row_coverage_percent", 0.0),
            "missing_beams": excel.get("missing_beams", 0),
            "missing_rows": excel.get("missing_rows", 0),
            "missing_values": excel.get("missing_values", 0),
            "generated_steel_kg": steel.get("generated_steel_kg", 0.0),
            "estimator_steel_kg": steel.get("estimator_steel_kg", 0.0),
            "steel_quantity_coverage_percent": steel.get("accuracy_percent", 0.0),
            "steel_difference_kg": steel.get("difference_kg", 0.0),
            "steel_difference_percent": steel.get("difference_percent", 0.0),
            "official_total_steel_estimator": result.get("official_quantity_summary", {}).get("estimator", {}).get("total"),
            "official_total_steel_generated": result.get("official_quantity_summary", {}).get("generated", {}).get("total"),
            "quantity_source": result.get("quantity_source"),
            "schedule_row_aggregation_used": result.get("schedule_row_aggregation_used", False),
            "diameter_coverage_summary": result.get("diameter_coverage", {}).get("summary", {}),
            "engineering_pipeline_frozen": result.get("engineering_pipeline_frozen", True),
            "engineering_code_modified": result.get("engineering_code_modified", False),
            "parser_executed": result.get("parser_executed", False),
        }
