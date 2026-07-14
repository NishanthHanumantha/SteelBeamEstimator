"""
Phase V.A.1.1 — validation_reporter.py
Generates the 8-section recompute validation report.
MODEL_VERSION: 6.6.3
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List

from validation_recompute_models import (
    EngineeringAccuracyKPIs,
    FullRecomputeResult,
    PipelineRecomputeResult,
    RecomputeStatistics,
    ValidationDifferenceReport,
    WorkbookDiffResult,
    WorkbookRecomputeValidation,
)

# ── Previous V.A.1 baseline KPIs (MODEL_VERSION 6.5.3) ───────────────────────
_PREV = {
    "model_version": "6.5.3",
    "pipeline_status": "PARTIAL",
    "stages_passed": 4,
    "stages_total": 5,
    "workbook_match_pct": 36.8464,
    "steel_weight_kg": 0.0,
    "bbs_rows": 152,
    "reference_bbs_rows": 252,
    "stirrup_beams": 5,
    "total_engineering_rows": 144,
    "bbs_completeness_pct": 0.0,
    "col_count_delta": 7,
}


class ValidationReporter:
    """
    Assembles the full 8-section JSON report for Phase V.A.1.1.
    """

    def build(self, result: FullRecomputeResult) -> Dict[str, Any]:
        pipe = result.pipeline
        wb   = result.workbook_validation
        diff = result.workbook_diff
        eng  = result.engineering_accuracy
        dr   = result.difference_report
        stat = result.statistics

        report: Dict[str, Any] = {
            "model_version": result.model_version,
            "benchmark_id":  result.benchmark_id,
            "timestamp":     result.timestamp,
            "drawing_name":  result.drawing_name,
        }

        report["section_1_executive_summary"] = self._section1(pipe, wb, diff, eng, stat)
        report["section_2_pipeline_summary"]  = self._section2(pipe)
        report["section_3_workbook_validation"] = self._section3(wb)
        report["section_4_engineering_accuracy"] = self._section4(eng)
        report["section_5_workbook_comparison"]  = self._section5(diff)
        report["section_6_difference_from_previous"] = self._section6(dr)
        report["section_7_remaining_engineering_gaps"] = self._section7(result)
        report["section_8_readiness_assessment"] = self._section8(result)

        return report

    # ── Section 1 — Executive Summary ────────────────────────────────────────
    def _section1(
        self,
        pipe: PipelineRecomputeResult,
        wb:   WorkbookRecomputeValidation,
        diff: WorkbookDiffResult,
        eng:  EngineeringAccuracyKPIs,
        stat: RecomputeStatistics,
    ) -> Dict[str, Any]:
        return {
            "title": "Phase V.A.1.1 — End-to-End Validation Recompute (Benchmark Set 1)",
            "pipeline_status": "PASS" if pipe.pipeline_passed else "PARTIAL",
            "workbook_generated": wb.exists if wb else False,
            "workbook_valid": wb.validation_passed if wb else False,
            "overall_match_rate_pct": diff.overall_match_rate_pct if diff else 0.0,
            "steel_weight_kg": eng.total_steel_kg if eng else 0.0,
            "stirrup_coverage_beams": eng.stirrup_coverage_beams if eng else 0,
            "bbs_rows_generated": eng.total_bbs_rows if eng else 0,
            "total_pipeline_seconds": pipe.total_elapsed_seconds if pipe else 0.0,
            "stages_passed": pipe.stages_passed if pipe else 0,
            "stages_total": pipe.stages_executed if pipe else 0,
            "validation_passed": result_passed(pipe, wb, diff, eng),
            "ready_for_benchmark_set_2": self._readiness(eng, diff),
            "note": (
                "Phase V.A.1.1 recomputes the complete engineering validation "
                "for Benchmark Set 1 using MODEL_VERSION 6.6.2 pipeline "
                "(V.B.1 + SI.1 + SI.0). No engineering logic was modified."
            ),
        }

    # ── Section 2 — Pipeline Summary ─────────────────────────────────────────
    def _section2(self, pipe: PipelineRecomputeResult) -> Dict[str, Any]:
        if not pipe:
            return {}
        stages_out = []
        for s in pipe.stages:
            stages_out.append({
                "name":            s.stage_name,
                "success":         s.success,
                "exit_code":       s.exit_code,
                "elapsed_seconds": s.elapsed_seconds,
                "stdout_lines":    s.stdout_lines,
                "output_files":    s.output_files,
                "error":           s.error_message,
            })
        return {
            "stages_executed":    pipe.stages_executed,
            "stages_passed":      pipe.stages_passed,
            "stages_failed":      pipe.stages_failed,
            "total_elapsed_sec":  pipe.total_elapsed_seconds,
            "success_rate_pct":   pipe.success_rate_pct,
            "pipeline_passed":    pipe.pipeline_passed,
            "stages":             stages_out,
        }

    # ── Section 3 — Workbook Validation ──────────────────────────────────────
    def _section3(self, wb: WorkbookRecomputeValidation) -> Dict[str, Any]:
        if not wb:
            return {"validation_passed": False, "issues": ["Workbook not validated"]}
        ws_out = []
        for w in wb.worksheet_validations:
            ws_out.append({
                "sheet_name":       w.sheet_name,
                "row_count":        w.row_count,
                "col_count":        w.col_count,
                "has_headers":      w.has_headers,
                "has_data_rows":    w.has_data_rows,
                "has_totals":       w.has_totals_row,
                "has_steel_summary": w.has_steel_summary,
                "validation_passed": w.validation_passed,
                "issues":           w.issues,
            })
        return {
            "workbook_path":     wb.workbook_path,
            "exists":            wb.exists,
            "readable":          wb.readable,
            "corrupted":         wb.corrupted,
            "size_bytes":        wb.size_bytes,
            "size_kb":           wb.size_kb,
            "sheet_names":       wb.sheet_names,
            "total_sheets":      wb.total_sheets,
            "total_rows":        wb.total_rows,
            "total_columns":     wb.total_columns,
            "has_data":          wb.has_data,
            "validation_passed": wb.validation_passed,
            "worksheet_validations": ws_out,
            "issues":            wb.issues,
        }

    # ── Section 4 — Engineering Accuracy ─────────────────────────────────────
    def _section4(self, eng: EngineeringAccuracyKPIs) -> Dict[str, Any]:
        if not eng:
            return {}
        return {
            "total_beams":              eng.total_beams,
            "beams_with_top_bars":      eng.beams_with_top_bars,
            "beams_with_bottom_bars":   eng.beams_with_bottom_bars,
            "beams_with_extra_bars":    eng.beams_with_extra_bars,
            "beams_with_stirrups":      eng.beams_with_stirrups,
            "beams_with_development_bars": eng.beams_with_development_bars,
            "beams_with_lap_bars":      eng.beams_with_lap_bars,
            "beams_with_spacer_bars":   eng.beams_with_spacer_bars,
            "total_engineering_rows":   eng.total_engineering_rows,
            "total_bbs_rows":           eng.total_bbs_rows,
            "total_steel_kg":           eng.total_steel_kg,
            "project_total_kg":         eng.project_total_kg,
            "workbook_match_pct":       eng.workbook_match_pct,
            "stirrup_coverage_beams":   eng.stirrup_coverage_beams,
            "bbs_completeness_pct":     eng.bbs_completeness_pct,
            "diameter_totals_kg":       eng.diameter_totals_kg,
        }

    # ── Section 5 — Workbook Comparison ──────────────────────────────────────
    def _section5(self, diff: WorkbookDiffResult) -> Dict[str, Any]:
        if not diff:
            return {"comparison_completed": False}
        ws_comps = []
        for w in diff.worksheet_diffs:
            ws_comps.append({
                "sheet_name":        w.sheet_name,
                "generated_rows":    w.generated_rows,
                "reference_rows":    w.reference_rows,
                "generated_cols":    w.generated_cols,
                "reference_cols":    w.reference_cols,
                "row_count_match":   w.row_count_match,
                "col_count_match":   w.col_count_match,
                "header_match":      w.header_match,
                "data_rows_compared": w.data_rows_compared,
                "matching_cells":    w.matching_cells,
                "mismatching_cells": w.mismatching_cells,
                "match_rate_pct":    w.match_rate_pct,
                "key_mismatches":    w.key_mismatches,
            })
        return {
            "generated_path":       diff.generated_path,
            "reference_path":       diff.reference_path,
            "generated_sheets":     diff.generated_sheets,
            "reference_sheets":     diff.reference_sheets,
            "sheet_count_match":    diff.sheet_count_match,
            "sheet_names_match":    diff.sheet_names_match,
            "common_sheets":        diff.common_sheets,
            "missing_in_generated": diff.missing_in_generated,
            "extra_in_generated":   diff.extra_in_generated,
            "overall_match_rate_pct": diff.overall_match_rate_pct,
            "worksheet_comparisons": ws_comps,
            "comparison_completed": diff.comparison_completed,
        }

    # ── Section 6 — Difference from Previous Validation ──────────────────────
    def _section6(self, dr: ValidationDifferenceReport) -> Dict[str, Any]:
        if not dr:
            return {}

        def _fmt(m_list: list) -> list:
            return [
                {
                    "metric":   m.metric_name,
                    "previous": m.previous_value,
                    "current":  m.current_value,
                    "change":   m.change,
                    "direction": m.direction,
                    "major":    m.is_major,
                }
                for m in m_list
            ]

        return {
            "previous_model_version": dr.previous_model_version,
            "current_model_version":  dr.current_model_version,
            "improved_metrics":  _fmt(dr.improved_metrics),
            "unchanged_metrics": _fmt(dr.unchanged_metrics),
            "regression_metrics": _fmt(dr.regression_metrics),
            "new_metrics":       _fmt(dr.new_metrics),
            "major_improvements": dr.major_improvements,
        }

    # ── Section 7 — Remaining Engineering Gaps ───────────────────────────────
    def _section7(self, result: FullRecomputeResult) -> Dict[str, Any]:
        gaps = result.remaining_gaps or []
        blockers     = [g for g in gaps if "BLOCK" in g.upper() or "CRITICAL" in g.upper()]
        non_blockers = [g for g in gaps if g not in blockers]
        return {
            "total_gaps":    len(gaps),
            "blockers":      blockers,
            "non_blockers":  non_blockers,
            "gap_details":   gaps,
        }

    # ── Section 8 — Readiness Assessment ─────────────────────────────────────
    def _section8(self, result: FullRecomputeResult) -> Dict[str, Any]:
        ra = result.readiness_assessment or {}
        return ra

    # ── helpers ───────────────────────────────────────────────────────────────
    def _readiness(
        self,
        eng: EngineeringAccuracyKPIs,
        diff: WorkbookDiffResult,
    ) -> bool:
        if not eng or not diff:
            return False
        return (
            eng.total_steel_kg > 0
            and eng.stirrup_coverage_beams > 0
            and diff.overall_match_rate_pct > 50.0
        )


def result_passed(pipe, wb, diff, eng) -> bool:
    return (
        (pipe is not None and pipe.pipeline_passed)
        and (wb is not None and wb.validation_passed)
        and (diff is not None and diff.comparison_completed)
        and (eng is not None and eng.total_steel_kg > 0)
    )
