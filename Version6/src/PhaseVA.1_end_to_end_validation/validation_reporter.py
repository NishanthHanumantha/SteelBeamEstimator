"""
Phase V.A.1 — End-to-End Validation
validation_reporter.py — Build the 8-section validation report.
MODEL_VERSION: 6.5.3
"""
from __future__ import annotations

from typing import Any, Dict, List

from validation_models import (
    StageResult, ValidationSummary, WorkbookComparison,
    WorkbookValidation, WorksheetValidation
)


class ValidationReporter:
    """Generates an 8-section end-to-end validation report."""

    def build_report(
        self,
        summary: ValidationSummary,
        stage_results: List[StageResult],
        workbook_val: WorkbookValidation,
        worksheet_vals: List[WorksheetValidation],
        pipeline_outputs: List[Dict[str, Any]],
        workbook_comp: WorkbookComparison,
        statistics: Dict[str, Any],
    ) -> Dict[str, Any]:

        return {
            "model_version": summary.model_version,
            "benchmark_id": summary.benchmark_id,
            "drawing_name": summary.drawing_name,
            "timestamp": summary.timestamp,

            # ── Section 1: Executive Summary ──────────────────────────────
            "section_1_executive_summary": {
                "title": "Phase V.A.1 — End-to-End Validation",
                "pipeline_status": "PASS" if summary.stages_passed == summary.stages_executed else "PARTIAL",
                "workbook_generated": summary.workbook_generated,
                "workbook_valid": summary.workbook_valid,
                "worksheet_pass_rate_pct": summary.worksheet_pass_rate_pct,
                "comparison_match_rate_pct": summary.overall_match_rate_pct,
                "validation_passed": summary.validation_passed,
                "ready_for_benchmark_set_2": summary.ready_for_benchmark_set_2,
                "total_pipeline_seconds": summary.total_pipeline_seconds,
                "note": (
                    "Phase V.A.1 validates the complete production pipeline end-to-end. "
                    "No engineering logic was modified. "
                    "All differences are observed and reported — not corrected."
                ),
            },

            # ── Section 2: Pipeline Execution ─────────────────────────────
            "section_2_pipeline_execution": {
                "stages_executed": summary.stages_executed,
                "stages_passed": summary.stages_passed,
                "stages_failed": summary.stages_failed,
                "total_elapsed_seconds": summary.total_pipeline_seconds,
                "success_rate_pct": statistics["pipeline_success_rate_pct"],
                "stages": [
                    {
                        "name": r.stage_name,
                        "success": r.success,
                        "exit_code": r.exit_code,
                        "elapsed_seconds": r.elapsed_seconds,
                        "stdout_lines": r.stdout_lines,
                        "output_files_found": r.output_files,
                        "error": r.error_message,
                    }
                    for r in stage_results
                ],
                "pipeline_outputs": pipeline_outputs,
            },

            # ── Section 3: Workbook Validation ────────────────────────────
            "section_3_workbook_validation": {
                "workbook_path": workbook_val.workbook_path,
                "exists": workbook_val.exists,
                "readable": workbook_val.readable,
                "corrupted": workbook_val.corrupted,
                "size_bytes": workbook_val.size_bytes,
                "size_kb": round(workbook_val.size_bytes / 1024, 1),
                "sheet_names": workbook_val.sheet_names,
                "total_sheets": workbook_val.total_sheets,
                "total_rows": workbook_val.total_rows,
                "total_columns": workbook_val.total_columns,
                "has_data": workbook_val.has_data,
                "validation_passed": workbook_val.validation_passed,
                "issues": workbook_val.issues,
            },

            # ── Section 4: Worksheet Validation ───────────────────────────
            "section_4_worksheet_validation": {
                "worksheets_validated": len(worksheet_vals),
                "worksheets_passed": sum(1 for w in worksheet_vals if w.validation_passed),
                "worksheets": [
                    {
                        "sheet_name": w.sheet_name,
                        "row_count": w.row_count,
                        "col_count": w.col_count,
                        "has_headers": w.has_headers,
                        "has_data_rows": w.has_data_rows,
                        "validation_passed": w.validation_passed,
                        "issues": w.issues,
                    }
                    for w in worksheet_vals
                ],
            },

            # ── Section 5: Workbook Comparison ────────────────────────────
            "section_5_workbook_comparison": {
                "generated_path": workbook_comp.generated_path,
                "reference_path": workbook_comp.reference_path,
                "generated_sheets": workbook_comp.generated_sheets,
                "reference_sheets": workbook_comp.reference_sheets,
                "sheet_count_match": workbook_comp.sheet_count_match,
                "sheet_names_match": workbook_comp.sheet_names_match,
                "common_sheets": workbook_comp.common_sheets,
                "missing_in_generated": workbook_comp.missing_in_generated,
                "extra_in_generated": workbook_comp.extra_in_generated,
                "overall_match_rate_pct": workbook_comp.overall_match_rate_pct,
                "worksheet_comparisons": [
                    {
                        "sheet_name": wc.sheet_name,
                        "generated_rows": wc.gen_rows,
                        "reference_rows": wc.ref_rows,
                        "generated_cols": wc.gen_cols,
                        "reference_cols": wc.ref_cols,
                        "row_count_match": wc.row_count_match,
                        "col_count_match": wc.col_count_match,
                        "header_match": wc.header_match,
                        "data_rows_compared": wc.data_rows_compared,
                        "matching_cells": wc.matching_cells,
                        "mismatching_cells": wc.mismatching_cells,
                        "match_rate_pct": wc.match_rate_pct,
                    }
                    for wc in workbook_comp.worksheet_comparisons
                ],
            },

            # ── Section 6: Engineering Differences ────────────────────────
            "section_6_engineering_differences": {
                "steel_weight_comparison": workbook_comp.steel_weight_comparison,
                "quantity_comparison": workbook_comp.quantity_comparison,
                "row_count_delta": abs(
                    sum(wc.gen_rows for wc in workbook_comp.worksheet_comparisons) -
                    sum(wc.ref_rows for wc in workbook_comp.worksheet_comparisons)
                ),
                "col_count_delta": abs(
                    max((wc.gen_cols for wc in workbook_comp.worksheet_comparisons), default=0) -
                    max((wc.ref_cols for wc in workbook_comp.worksheet_comparisons), default=0)
                ),
                "key_cell_differences": _top_diffs(workbook_comp),
                "observed_differences": summary.engineering_differences,
            },

            # ── Section 7: Observed Issues ────────────────────────────────
            "section_7_observed_issues": {
                "blockers": summary.blockers,
                "non_blockers": [i for i in workbook_val.issues if i not in summary.blockers],
                "comparison_issues": _comparison_issues(workbook_comp),
            },

            # ── Section 8: Recommendations ────────────────────────────────
            "section_8_recommendations": {
                "recommendations": summary.recommendations,
                "ready_for_benchmark_set_2": summary.ready_for_benchmark_set_2,
                "readiness_rationale": _readiness_rationale(summary),
            },
        }


def _top_diffs(comp: WorkbookComparison) -> List[Dict]:
    diffs: List[Dict] = []
    for wc in comp.worksheet_comparisons:
        for d in wc.key_differences[:5]:
            diffs.append({**d, "sheet": wc.sheet_name})
    return diffs[:20]


def _comparison_issues(comp: WorkbookComparison) -> List[str]:
    issues = []
    if comp.missing_in_generated:
        issues.append(f"Sheets missing in generated workbook: {comp.missing_in_generated}")
    if comp.extra_in_generated:
        issues.append(f"Extra sheets in generated workbook not in reference: {comp.extra_in_generated}")
    sw = comp.steel_weight_comparison
    if sw and not sw.get("match"):
        issues.append(
            f"Steel weight total mismatch: generated={sw.get('generated_total')}, "
            f"reference={sw.get('reference_total')}, diff={sw.get('difference_pct')}%"
        )
    return issues


def _readiness_rationale(summary: ValidationSummary) -> str:
    if summary.ready_for_benchmark_set_2:
        return (
            "Pipeline executes end-to-end successfully. "
            "Workbook is generated and validated. "
            "Engineering differences are within expected range for the current accuracy sprint. "
            "Proceed to Benchmark Set 2."
        )
    blockers = summary.blockers
    if blockers:
        return (
            f"Not ready for Benchmark Set 2 due to: {blockers[0]}. "
            "Resolve blockers, then re-run V.A.1 validation."
        )
    return (
        "Pipeline partially passes. "
        "Address observed issues (steel weight calculation deferred, "
        "row count delta vs reference) before Benchmark Set 2. "
        "These are known gaps from QA.1.1 diagnostics."
    )
