"""
parser_correction_export.py — Export V.TEST.3.2.1 parser correction artefacts.
MODEL_VERSION: 8.1.3
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import asdict
from typing import Any, Dict

from comparison_models import ComparisonResult

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_OUTPUT = _ROOT / "Version7" / "data" / "output" / "PhaseVTEST3_2_1_parser_correction"


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


class ParserCorrectionExport:

    def __init__(self, output_dir: pathlib.Path = _OUTPUT) -> None:
        self._out = output_dir
        self._out.mkdir(parents=True, exist_ok=True)

    def export_all(
        self,
        result: ComparisonResult,
        summary_validation: Dict[str, Any],
        parser_validation: Dict[str, Any],
        corrections: Dict[str, Any],
        md_report: str,
    ) -> Dict[str, pathlib.Path]:
        paths: Dict[str, pathlib.Path] = {}

        artefacts = {
            "parser_correction_summary.json": corrections,
            "corrected_summary_table.json": result.summary_comparison,
            "corrected_accuracy_metrics.json": result.accuracy_metrics,
            "corrected_diameter_comparison.json": {"diameters": result.diameter_comparison},
            "corrected_similarity_score.json": {
                "overall_estimator_similarity_score": result.accuracy_metrics.get(
                    "overall_estimator_similarity_score"
                ),
                "overall_steel_accuracy_pct": result.accuracy_metrics.get("overall_steel_accuracy_pct"),
                "project_accuracy_pct": result.accuracy_metrics.get("project_accuracy_pct"),
                "scope_note": result.accuracy_metrics.get("scope_note"),
            },
            "parser_validation.json": parser_validation,
        }

        for filename, data in artefacts.items():
            p = self._out / filename
            payload = {
                **data,
                "summary_table_validation": summary_validation,
            } if filename == "corrected_summary_table.json" else data
            p.write_text(json.dumps(_safe(payload), indent=2, default=str), encoding="utf-8")
            paths[filename] = p

        md_path = self._out / "parser_correction_report.md"
        md_path.write_text(md_report, encoding="utf-8")
        paths["parser_correction_report.md"] = md_path

        return paths
