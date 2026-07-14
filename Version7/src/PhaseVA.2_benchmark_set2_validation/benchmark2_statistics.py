"""
Phase V.A.2 -- benchmark2_statistics.py
Aggregate all pipeline, engineering, workbook, and comparison statistics.
MODEL_VERSION: 7.0.0
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, Optional

from benchmark2_models import (
    EngineeringKPIs,
    PipelineRunResult,
    WorkbookComparison,
    WorkbookValidation,
)

_ROOT    = pathlib.Path(__file__).resolve().parents[3]
_V7      = _ROOT / "Version7"
_VA11    = _V7   / "data/output/PhaseVA.1.1_end_to_end_validation_recompute"


def _load_json(path: pathlib.Path) -> Optional[Any]:
    if not path.exists() or path.stat().st_size < 3:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


class Benchmark2Statistics:
    """Collect and aggregate all statistics for Benchmark Set 2."""

    def collect(
        self,
        pipeline: PipelineRunResult,
        workbook_val: WorkbookValidation,
        eng_kpis: EngineeringKPIs,
        wb_comparison: WorkbookComparison,
    ) -> Dict[str, Any]:

        pipeline_stats = self._pipeline_stats(pipeline)
        engineering_stats = self._engineering_stats(eng_kpis)
        workbook_stats = self._workbook_stats(workbook_val)
        comparison_stats = self._comparison_stats(wb_comparison)
        set1_stats = self._load_benchmark_set1_stats()

        return {
            "pipeline": pipeline_stats,
            "engineering": engineering_stats,
            "workbook": workbook_stats,
            "comparison": comparison_stats,
            "benchmark_set1_baseline": set1_stats,
        }

    def _pipeline_stats(self, p: PipelineRunResult) -> Dict[str, Any]:
        stage_breakdown = []
        for s in p.stages:
            stage_breakdown.append({
                "stage": s.stage_name,
                "success": s.success,
                "elapsed_s": s.elapsed_seconds,
                "exit_code": s.exit_code,
                "output_files": s.output_files,
                "error": s.error_message if s.error_message else None,
            })
        return {
            "total_elapsed_s": p.total_elapsed_seconds,
            "stages_executed": p.stages_executed,
            "stages_passed": p.stages_passed,
            "stages_failed": p.stages_failed,
            "success_rate_pct": p.success_rate_pct,
            "pipeline_passed": p.pipeline_passed,
            "stage_breakdown": stage_breakdown,
        }

    def _engineering_stats(self, k: EngineeringKPIs) -> Dict[str, Any]:
        return {
            "total_beams": k.total_beams,
            "total_engineering_rows": k.total_engineering_rows,
            "total_bbs_rows": k.total_bbs_rows,
            "total_steel_kg": k.total_steel_kg,
            "stirrup_coverage_beams": k.stirrup_coverage_beams,
            "bbs_completeness_pct": k.bbs_completeness_pct,
            "diameter_totals_kg": k.diameter_totals_kg,
            "data_source": k.data_source,
        }

    def _workbook_stats(self, wv: WorkbookValidation) -> Dict[str, Any]:
        return {
            "exists": wv.exists,
            "readable": wv.readable,
            "size_kb": wv.size_kb,
            "total_sheets": wv.total_sheets,
            "total_rows": wv.total_rows,
            "sheet_names": wv.sheet_names,
            "has_data": wv.has_data,
            "validation_passed": wv.validation_passed,
            "issues": wv.issues,
        }

    def _comparison_stats(self, wc: WorkbookComparison) -> Dict[str, Any]:
        return {
            "reference_exists": wc.reference_exists,
            "comparison_completed": wc.comparison_completed,
            "overall_match_rate_pct": wc.overall_match_rate_pct,
            "common_sheets": wc.common_sheets,
            "note": wc.note,
        }

    def _load_benchmark_set1_stats(self) -> Dict[str, Any]:
        """Load Benchmark Set 1 KPIs from V.A.1.1 report for comparison."""
        report = _load_json(_VA11 / "validation_report.json")
        if not report:
            return {
                "source": "V.A.1.1 report not found -- using hardcoded V.A.1.1 KPIs",
                "model_version": "6.6.3",
                "total_beams": 18,
                "total_steel_kg": 2027.94,
                "total_bbs_rows": 0,
                "stirrup_coverage_beams": 18,
                "bbs_completeness_pct": 0.0,
                "pipeline_success_rate_pct": 100.0,
                "workbook_generated": True,
            }
        # Extract key KPIs from the V.A.1.1 report structure
        exec_sum = report.get("executive_summary") or {}
        eng      = report.get("engineering_accuracy") or {}
        pipe     = report.get("pipeline_summary") or {}
        return {
            "source": "Version7/data/output/PhaseVA.1.1_end_to_end_validation_recompute/validation_report.json",
            "model_version": exec_sum.get("model_version", "6.6.3"),
            "total_beams": eng.get("total_beams", 18),
            "total_steel_kg": eng.get("total_steel_kg", 2027.94),
            "total_bbs_rows": eng.get("total_bbs_rows", 0),
            "stirrup_coverage_beams": eng.get("stirrup_coverage_beams", 18),
            "bbs_completeness_pct": eng.get("bbs_completeness_pct", 0.0),
            "pipeline_success_rate_pct": pipe.get("success_rate_pct", 100.0),
            "workbook_generated": exec_sum.get("workbook_generated", True),
        }
