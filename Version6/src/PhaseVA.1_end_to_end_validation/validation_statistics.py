"""
Phase V.A.1 — End-to-End Validation
validation_statistics.py — Compute validation statistics.
MODEL_VERSION: 6.5.3
"""
from __future__ import annotations

from typing import Any, Dict, List

from validation_models import (
    StageResult, WorkbookComparison, WorkbookValidation, WorksheetValidation
)


class ValidationStatistics:
    """Computes aggregate statistics over the full validation run."""

    def compute(
        self,
        stage_results: List[StageResult],
        workbook_val: WorkbookValidation,
        worksheet_vals: List[WorksheetValidation],
        pipeline_output_checks: List[Dict[str, Any]],
        workbook_comp: WorkbookComparison,
    ) -> Dict[str, Any]:

        # Pipeline
        stages_total = len(stage_results)
        stages_passed = sum(1 for r in stage_results if r.success)
        total_time = sum(r.elapsed_seconds for r in stage_results)

        # Workbook
        wb_generated = workbook_val.exists
        wb_valid = workbook_val.validation_passed
        wb_size = workbook_val.size_bytes

        # Worksheets
        ws_total = len(worksheet_vals)
        ws_passed = sum(1 for w in worksheet_vals if w.validation_passed)
        ws_pass_rate = round(100 * ws_passed / ws_total, 2) if ws_total else 0.0

        # Pipeline outputs
        outputs_total = len(pipeline_output_checks)
        outputs_found = sum(1 for o in pipeline_output_checks if o["exists"])
        outputs_rate = round(100 * outputs_found / outputs_total, 2) if outputs_total else 0.0

        # Comparison
        comp = workbook_comp
        gen_rows_total = sum(wc.gen_rows for wc in comp.worksheet_comparisons)
        ref_rows_total = sum(wc.ref_rows for wc in comp.worksheet_comparisons)

        return {
            # Pipeline execution
            "pipeline_execution_time_seconds": round(total_time, 2),
            "pipeline_success_rate_pct": round(100 * stages_passed / stages_total, 2) if stages_total else 0.0,
            "stages_executed": stages_total,
            "stages_passed": stages_passed,
            "stages_failed": stages_total - stages_passed,

            # Workbook
            "workbook_generated": wb_generated,
            "workbook_valid": wb_valid,
            "workbook_size_bytes": wb_size,
            "workbook_sheets": workbook_val.total_sheets,
            "workbook_rows": workbook_val.total_rows,

            # Pipeline outputs
            "pipeline_outputs_found": outputs_found,
            "pipeline_outputs_expected": outputs_total,
            "pipeline_outputs_rate_pct": outputs_rate,

            # Worksheets
            "worksheet_success_rate_pct": ws_pass_rate,
            "worksheets_validated": ws_total,
            "worksheets_passed": ws_passed,

            # Comparison
            "comparison_completed": True,
            "generated_rows": gen_rows_total,
            "reference_rows": ref_rows_total,
            "row_count_match": gen_rows_total == ref_rows_total,
            "sheets_in_generated": len(comp.generated_sheets),
            "sheets_in_reference": len(comp.reference_sheets),
            "common_sheets": len(comp.common_sheets),
            "overall_match_rate_pct": comp.overall_match_rate_pct,
            "steel_weight_comparison": comp.steel_weight_comparison,
            "quantity_comparison": comp.quantity_comparison,
            "totals_match": comp.totals_match,

            # Per-sheet comparison summary
            "worksheet_comparison_summary": [
                {
                    "sheet": wc.sheet_name,
                    "gen_rows": wc.gen_rows,
                    "ref_rows": wc.ref_rows,
                    "gen_cols": wc.gen_cols,
                    "ref_cols": wc.ref_cols,
                    "row_match": wc.row_count_match,
                    "header_match": wc.header_match,
                    "data_rows_compared": wc.data_rows_compared,
                    "matching_cells": wc.matching_cells,
                    "mismatching_cells": wc.mismatching_cells,
                    "match_rate_pct": wc.match_rate_pct,
                }
                for wc in comp.worksheet_comparisons
            ],
        }
