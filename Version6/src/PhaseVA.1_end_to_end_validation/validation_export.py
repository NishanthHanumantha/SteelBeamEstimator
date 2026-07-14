"""
Phase V.A.1 — End-to-End Validation
validation_export.py — Export 7 JSON validation reports.
MODEL_VERSION: 6.5.3
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_OUT = _ROOT / "Version6" / "data" / "output" / "PhaseVA.1_end_to_end_validation"


def _write(path: pathlib.Path, data: Any) -> None:
    _OUT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


class ValidationExport:
    """Writes all 7 validation report files."""

    def export_all(
        self,
        full_report: Dict[str, Any],
        stage_results_data: Dict[str, Any],
        workbook_val_data: Dict[str, Any],
        worksheet_val_data: Dict[str, Any],
        workbook_comp_data: Dict[str, Any],
        statistics: Dict[str, Any],
        engineering_diffs: Dict[str, Any],
        model_version: str,
        benchmark_id: str,
        timestamp: str,
    ) -> Dict[str, str]:
        meta = {
            "model_version": model_version,
            "benchmark_id": benchmark_id,
            "timestamp": timestamp,
        }
        paths: Dict[str, str] = {}

        def wp(name: str, data: Any) -> None:
            p = _OUT / name
            _write(p, {**meta, **data} if isinstance(data, dict) else data)
            paths[name] = str(p)

        # 1. Full end-to-end report
        wp("end_to_end_validation_report.json", full_report)

        # 2. Pipeline execution
        wp("pipeline_execution_report.json", stage_results_data)

        # 3. Workbook validation
        wp("workbook_validation_report.json", workbook_val_data)

        # 4. Worksheet validation
        wp("worksheet_validation_report.json", worksheet_val_data)

        # 5. Workbook comparison
        wp("workbook_comparison_report.json", workbook_comp_data)

        # 6. Validation statistics
        wp("validation_statistics.json", statistics)

        # 7. Engineering differences
        wp("engineering_difference_report.json", engineering_diffs)

        return paths
