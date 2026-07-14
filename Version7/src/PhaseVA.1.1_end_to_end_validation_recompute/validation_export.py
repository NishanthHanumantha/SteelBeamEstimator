"""
Phase V.A.1.1 — validation_export.py
Exports all 6 JSON artefacts produced by the recompute phase.
MODEL_VERSION: 6.6.3
"""
from __future__ import annotations

import json
import pathlib
from datetime import datetime
from typing import Any, Dict

from validation_recompute_models import (
    EngineeringAccuracyKPIs,
    FullRecomputeResult,
    RecomputeStatistics,
    ValidationDifferenceReport,
    WorkbookDiffResult,
)

_ROOT    = pathlib.Path(__file__).resolve().parents[3]
_OUT_DIR = _ROOT / "Version7/data/output/PhaseVA.1.1_end_to_end_validation_recompute"


def _dump(data: Any, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, default=str, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"    Exported -> {path.relative_to(_ROOT)}")


class ValidationExporter:
    """
    Writes 6 JSON artefacts to the V.A.1.1 output directory.
    """

    def __init__(self, output_dir: pathlib.Path = _OUT_DIR) -> None:
        self._out = output_dir

    def export_all(
        self,
        full_report:    Dict[str, Any],
        eng_accuracy:   EngineeringAccuracyKPIs,
        wb_diff:        WorkbookDiffResult,
        diff_report:    ValidationDifferenceReport,
        statistics:     RecomputeStatistics,
        result:         FullRecomputeResult,
    ) -> Dict[str, str]:
        paths: Dict[str, str] = {}

        # 1. End-to-End Validation Report v2
        p1 = self._out / "end_to_end_validation_report_v2.json"
        _dump(full_report, p1)
        paths["end_to_end_validation_report_v2"] = str(p1)

        # 2. Engineering Accuracy Summary
        p2 = self._out / "engineering_accuracy_summary.json"
        _dump(self._eng_accuracy_dict(eng_accuracy), p2)
        paths["engineering_accuracy_summary"] = str(p2)

        # 3. Workbook Comparison Report
        p3 = self._out / "workbook_comparison_report.json"
        _dump(self._wb_diff_dict(wb_diff), p3)
        paths["workbook_comparison_report"] = str(p3)

        # 4. Difference from Previous Validation
        p4 = self._out / "difference_from_previous_validation.json"
        _dump(self._diff_dict(diff_report), p4)
        paths["difference_from_previous_validation"] = str(p4)

        # 5. Validation Statistics
        p5 = self._out / "validation_statistics.json"
        _dump(self._stats_dict(statistics), p5)
        paths["validation_statistics"] = str(p5)

        # 6. Production Readiness Report
        p6 = self._out / "production_readiness_report.json"
        _dump(self._readiness_dict(result), p6)
        paths["production_readiness_report"] = str(p6)

        return paths

    # ── serialisation helpers ─────────────────────────────────────────────────

    def _eng_accuracy_dict(self, e: EngineeringAccuracyKPIs) -> dict:
        return {
            "model_version": "6.6.3",
            "timestamp": datetime.now().isoformat(),
            "total_beams": e.total_beams,
            "beams_with_top_bars": e.beams_with_top_bars,
            "beams_with_bottom_bars": e.beams_with_bottom_bars,
            "beams_with_extra_bars": e.beams_with_extra_bars,
            "beams_with_stirrups": e.beams_with_stirrups,
            "beams_with_development_bars": e.beams_with_development_bars,
            "beams_with_lap_bars": e.beams_with_lap_bars,
            "beams_with_spacer_bars": e.beams_with_spacer_bars,
            "total_engineering_rows": e.total_engineering_rows,
            "total_bbs_rows": e.total_bbs_rows,
            "total_steel_kg": e.total_steel_kg,
            "project_total_kg": e.project_total_kg,
            "workbook_match_pct": e.workbook_match_pct,
            "stirrup_coverage_beams": e.stirrup_coverage_beams,
            "bbs_completeness_pct": e.bbs_completeness_pct,
            "diameter_totals_kg": e.diameter_totals_kg,
        }

    def _wb_diff_dict(self, d: WorkbookDiffResult) -> dict:
        ws = []
        for w in d.worksheet_diffs:
            ws.append({
                "sheet_name": w.sheet_name,
                "generated_rows": w.generated_rows,
                "reference_rows": w.reference_rows,
                "generated_cols": w.generated_cols,
                "reference_cols": w.reference_cols,
                "row_count_match": w.row_count_match,
                "col_count_match": w.col_count_match,
                "header_match": w.header_match,
                "data_rows_compared": w.data_rows_compared,
                "matching_cells": w.matching_cells,
                "mismatching_cells": w.mismatching_cells,
                "match_rate_pct": w.match_rate_pct,
                "key_mismatches": w.key_mismatches,
            })
        return {
            "model_version": "6.6.3",
            "timestamp": datetime.now().isoformat(),
            "generated_path": d.generated_path,
            "reference_path": d.reference_path,
            "generated_sheets": d.generated_sheets,
            "reference_sheets": d.reference_sheets,
            "sheet_count_match": d.sheet_count_match,
            "sheet_names_match": d.sheet_names_match,
            "common_sheets": d.common_sheets,
            "missing_in_generated": d.missing_in_generated,
            "extra_in_generated": d.extra_in_generated,
            "overall_match_rate_pct": d.overall_match_rate_pct,
            "comparison_completed": d.comparison_completed,
            "worksheet_comparisons": ws,
        }

    def _diff_dict(self, dr: ValidationDifferenceReport) -> dict:
        def fmt(ml):
            return [
                {
                    "metric": m.metric_name,
                    "previous": m.previous_value,
                    "current": m.current_value,
                    "change": m.change,
                    "direction": m.direction,
                    "major": m.is_major,
                }
                for m in ml
            ]
        return {
            "model_version": "6.6.3",
            "timestamp": datetime.now().isoformat(),
            "previous_model_version": dr.previous_model_version,
            "current_model_version": dr.current_model_version,
            "improved_metrics": fmt(dr.improved_metrics),
            "unchanged_metrics": fmt(dr.unchanged_metrics),
            "regression_metrics": fmt(dr.regression_metrics),
            "new_metrics": fmt(dr.new_metrics),
            "major_improvements": dr.major_improvements,
        }

    def _stats_dict(self, s: RecomputeStatistics) -> dict:
        return {
            "model_version": "6.6.3",
            "timestamp": datetime.now().isoformat(),
            "execution_time_sec": s.execution_time_sec,
            "pipeline_success": s.pipeline_success,
            "stages_passed": s.stages_passed,
            "stages_total": s.stages_total,
            "workbook_success": s.workbook_success,
            "worksheet_success": s.worksheet_success,
            "engineering_row_count": s.engineering_row_count,
            "total_steel_kg": s.total_steel_kg,
            "bbs_row_count": s.bbs_row_count,
            "workbook_match_pct": s.workbook_match_pct,
            "stirrup_beams": s.stirrup_beams,
            "diameter_totals_kg": s.diameter_totals_kg,
        }

    def _readiness_dict(self, result: FullRecomputeResult) -> dict:
        ra = result.readiness_assessment or {}
        return {
            "model_version": "6.6.3",
            "timestamp": datetime.now().isoformat(),
            "benchmark_id": result.benchmark_id,
            **ra,
        }
