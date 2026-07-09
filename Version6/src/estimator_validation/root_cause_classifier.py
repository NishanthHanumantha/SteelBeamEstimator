"""Root cause classification and fix recommendations — Phase QA.1."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.estimator_validation.audit_types import DiscrepancySeverity, RootCause


PHASE_FILE_HINTS = {
    RootCause.EXCEL_MAPPING: ("I.17", "Version6/src/excel_export/excel_export_builder.py"),
    RootCause.DISPLAY_ORDER: ("I.15", "Version6/src/engineering_calculations/beam_schedule/beam_schedule_types.py"),
    RootCause.ROW_INSERTION: ("I.17", "Version6/src/excel_export/excel_export_builder.py"),
    RootCause.TEMPLATE_LAYOUT: ("I.17", "Version6/src/excel_export/excel_export_builder.py"),
    RootCause.ENGINEERING_REPORT: ("I.16", "Version6/src/engineering_reports/engineering_report_builder.py"),
    RootCause.BEAM_SCHEDULE: ("I.15", "Version6/src/engineering_calculations/beam_schedule/beam_schedule_builder.py"),
    RootCause.MATERIAL: ("I.14", "Version6/src/engineering_calculations/material_quantification/material_builder.py"),
    RootCause.QUANTITY: ("I.13", "Version6/src/engineering_calculations/quantity/quantity_builder.py"),
    RootCause.STEEL_WEIGHT: ("I.11", "Version6/src/engineering_calculations/steel_weight/steel_weight_builder.py"),
    RootCause.BBS: ("I.10", "Version6/src/engineering_calculations/bbs/bbs_builder.py"),
    RootCause.ENGINEERING_CALCULATION: ("I.6-I.11", "Version6/src/engineering_calculations/"),
    RootCause.PARSER: ("G/H", "Version6/src/reinforcement/"),
    RootCause.DRAWING_DATA: ("Drawing", "Version6/data/framing/"),
    RootCause.GROUND_TRUTH_DIFFERENCE: ("QA", "Estimator validated workbook"),
    RootCause.UNKNOWN: ("QA", "Investigate manually"),
}


RISK_BY_ROOT_CAUSE = {
    RootCause.EXCEL_MAPPING: "LOW",
    RootCause.DISPLAY_ORDER: "LOW",
    RootCause.ROW_INSERTION: "LOW",
    RootCause.TEMPLATE_LAYOUT: "MEDIUM",
    RootCause.ENGINEERING_REPORT: "MEDIUM",
    RootCause.BEAM_SCHEDULE: "MEDIUM",
    RootCause.MATERIAL: "MEDIUM",
    RootCause.QUANTITY: "MEDIUM",
    RootCause.STEEL_WEIGHT: "HIGH",
    RootCause.BBS: "HIGH",
    RootCause.ENGINEERING_CALCULATION: "HIGH",
    RootCause.PARSER: "HIGH",
    RootCause.DRAWING_DATA: "HIGH",
    RootCause.GROUND_TRUTH_DIFFERENCE: "INFO",
    RootCause.UNKNOWN: "MEDIUM",
}


class RootCauseClassifier:
    """Assign one root cause per discrepancy using upstream trace evidence."""

    @staticmethod
    def classify_missing_generated_row(
        beam_mark: str,
        description: str,
        trace: dict[str, Any],
    ) -> RootCause:
        if trace.get("first_missing_layer"):
            layer = trace["first_missing_layer"]
            mapping = {
                "excel": RootCause.EXCEL_MAPPING,
                "engineering_report": RootCause.ENGINEERING_REPORT,
                "beam_schedule": RootCause.BEAM_SCHEDULE,
                "material": RootCause.MATERIAL,
                "quantity": RootCause.QUANTITY,
                "beam_summary": RootCause.ENGINEERING_CALCULATION,
                "steel_weight": RootCause.STEEL_WEIGHT,
                "bbs": RootCause.BBS,
            }
            return mapping.get(layer, RootCause.UNKNOWN)
        if trace.get("present_in_estimator_only"):
            return RootCause.GROUND_TRUTH_DIFFERENCE
        return RootCause.UNKNOWN

    @staticmethod
    def classify_value_difference(
        field: str,
        beam_mark: str,
        trace: dict[str, Any],
    ) -> RootCause:
        if field == "clear_span_m" and trace.get("engineering_report_clear_span_mm") is not None:
            if trace.get("generated_clear_span_m") == trace.get("engineering_report_clear_span_m"):
                return RootCause.GROUND_TRUTH_DIFFERENCE
            return RootCause.ENGINEERING_REPORT
        if trace.get("value_matches_engineering_report"):
            return RootCause.EXCEL_MAPPING
        if trace.get("value_matches_beam_schedule"):
            return RootCause.EXCEL_MAPPING
        if trace.get("first_missing_layer") == "engineering_report":
            return RootCause.ENGINEERING_REPORT
        if trace.get("first_missing_layer") == "beam_schedule":
            return RootCause.BEAM_SCHEDULE
        return RootCause.UNKNOWN

    @staticmethod
    def classify_structure_difference(category: str) -> RootCause:
        if category in {"merged_cell_count", "max_row", "worksheet_names"}:
            return RootCause.TEMPLATE_LAYOUT
        if category in {"column_widths", "page_margins", "freeze_panes", "print_area"}:
            return RootCause.TEMPLATE_LAYOUT
        return RootCause.TEMPLATE_LAYOUT

    @staticmethod
    def build_recommendation(
        problem: str,
        root_cause: RootCause,
        beam_mark: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        phase, file_path = PHASE_FILE_HINTS.get(root_cause, ("QA", ""))
        fix = {
            RootCause.EXCEL_MAPPING: "Adjust TemplateMapper cell mapping or row writer to preserve estimator row semantics.",
            RootCause.ENGINEERING_REPORT: "Verify EngineeringReport schedule_table copy includes all beam roles present in ground truth.",
            RootCause.BEAM_SCHEDULE: "Verify BeamSchedule row aggregation includes all reinforcement roles for the beam.",
            RootCause.STEEL_WEIGHT: "Trace missing bar groups or deferred calculations in steel weight engine.",
            RootCause.BBS: "Verify BBS rows exist for all reinforcement groups before schedule export.",
            RootCause.ENGINEERING_CALCULATION: "Investigate deferred/blocked calculation states for the beam in upstream phases.",
            RootCause.GROUND_TRUTH_DIFFERENCE: "Confirm estimator workbook assumptions; pipeline may be correct if drawing data differs.",
            RootCause.TEMPLATE_LAYOUT: "Align generated template section layout with estimator validated presentation structure.",
            RootCause.ROW_INSERTION: "Review dynamic row insertion and summary block spacing in excel export builder.",
        }.get(root_cause, "Investigate upstream trace and confirm first missing layer.")
        return {
            "problem": problem,
            "beam_mark": beam_mark,
            "description": description,
            "root_cause": root_cause.value,
            "recommended_phase": phase,
            "recommended_file": file_path,
            "recommended_fix": fix,
            "estimated_risk": RISK_BY_ROOT_CAUSE.get(root_cause, "MEDIUM"),
        }

    @staticmethod
    def severity_for(discrepancy_type: str, root_cause: RootCause) -> str:
        if discrepancy_type in {"missing_row", "missing_beam", "missing_generated_schedule"}:
            return DiscrepancySeverity.CRITICAL.value
        if discrepancy_type in {"value_difference", "extra_row"}:
            if root_cause in {RootCause.STEEL_WEIGHT, RootCause.BBS, RootCause.ENGINEERING_CALCULATION}:
                return DiscrepancySeverity.HIGH.value
            return DiscrepancySeverity.MEDIUM.value
        if discrepancy_type.startswith("presentation"):
            return DiscrepancySeverity.INFO.value
        return DiscrepancySeverity.MEDIUM.value
