"""
Phase V.A.1.1 — validation_statistics.py
Aggregates execution and validation statistics from the full recompute run.
MODEL_VERSION: 6.6.3
"""
from __future__ import annotations

from validation_recompute_models import (
    EngineeringAccuracyKPIs,
    PipelineRecomputeResult,
    RecomputeStatistics,
    WorkbookDiffResult,
    WorkbookRecomputeValidation,
)


class ValidationStatisticsCollector:
    """
    Derives a RecomputeStatistics record from all intermediate results.
    """

    def collect(
        self,
        pipeline: PipelineRecomputeResult,
        wb_validation: WorkbookRecomputeValidation,
        wb_diff: WorkbookDiffResult,
        eng_accuracy: EngineeringAccuracyKPIs,
    ) -> RecomputeStatistics:
        ws_success = (
            wb_validation.validation_passed
            and all(
                ws.validation_passed
                for ws in wb_validation.worksheet_validations
            )
        )

        return RecomputeStatistics(
            execution_time_sec=pipeline.total_elapsed_seconds,
            pipeline_success=pipeline.pipeline_passed,
            workbook_success=wb_validation.validation_passed,
            worksheet_success=ws_success,
            engineering_row_count=eng_accuracy.total_engineering_rows,
            total_steel_kg=eng_accuracy.total_steel_kg,
            bbs_row_count=eng_accuracy.total_bbs_rows,
            workbook_match_pct=wb_diff.overall_match_rate_pct,
            stages_passed=pipeline.stages_passed,
            stages_total=pipeline.stages_executed,
            stirrup_beams=eng_accuracy.stirrup_coverage_beams,
            diameter_totals_kg=eng_accuracy.diameter_totals_kg,
        )

    def to_dict(self, stats: RecomputeStatistics) -> dict:
        return {
            "execution_time_sec": stats.execution_time_sec,
            "pipeline_success": stats.pipeline_success,
            "stages_passed": stats.stages_passed,
            "stages_total": stats.stages_total,
            "workbook_success": stats.workbook_success,
            "worksheet_success": stats.worksheet_success,
            "engineering_row_count": stats.engineering_row_count,
            "total_steel_kg": stats.total_steel_kg,
            "bbs_row_count": stats.bbs_row_count,
            "workbook_match_pct": stats.workbook_match_pct,
            "stirrup_beams": stats.stirrup_beams,
            "diameter_totals_kg": stats.diameter_totals_kg,
        }
