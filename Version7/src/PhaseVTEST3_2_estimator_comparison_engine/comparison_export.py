"""
comparison_export.py — Export V.TEST.3.2 comparison artefacts.
MODEL_VERSION: 8.1.2
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import asdict
from typing import Any, Dict

from comparison_models import ComparisonResult

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_OUTPUT = _ROOT / "Version7" / "data" / "output" / "PhaseVTEST3_2_estimator_comparison"


def _safe(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _safe(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe(x) for x in obj]
    if isinstance(obj, pathlib.Path):
        return str(obj)
    return obj


class ComparisonExport:

    def __init__(self, output_dir: pathlib.Path = _OUTPUT) -> None:
        self._out = output_dir
        self._out.mkdir(parents=True, exist_ok=True)

    def export_all(
        self,
        result: ComparisonResult,
        md_report: str,
    ) -> Dict[str, pathlib.Path]:
        paths: Dict[str, pathlib.Path] = {}

        artefacts = {
            "estimator_summary_comparison.json": result.summary_comparison,
            "beam_level_comparison.json": {
                "beams": result.beam_comparisons,
                "count": len(result.beam_comparisons),
            },
            "diameter_comparison.json": {
                "diameters": result.diameter_comparison,
            },
            "role_comparison.json": {
                "roles": result.role_comparison,
            },
            "engineering_difference_report.json": {
                "differences": result.engineering_differences,
                "count": len(result.engineering_differences),
            },
            "beam_coverage_comparison.json": result.beam_coverage,
            "accuracy_metrics.json": result.accuracy_metrics,
            "root_cause_categories.json": result.root_causes,
            "comparison_dashboard.json": {
                "model_version": result.model_version,
                "phase_id": result.phase_id,
                "timestamp": result.timestamp,
                "model_workbook": _safe(result.model_workbook),
                "estimator_workbook": _safe(result.estimator_workbook),
                "accuracy_metrics": result.accuracy_metrics,
                "beam_coverage": result.beam_coverage,
                "validation": result.validation,
                "top_20_differences": result.top_20_differences,
                "recommended_investigation_order": result.recommended_investigation_order,
            },
        }

        for filename, data in artefacts.items():
            p = self._out / filename
            p.write_text(json.dumps(_safe(data), indent=2, default=str), encoding="utf-8")
            paths[filename] = p

        md_path = self._out / "estimator_vs_model_report.md"
        md_path.write_text(md_report, encoding="utf-8")
        paths["estimator_vs_model_report.md"] = md_path

        return paths
