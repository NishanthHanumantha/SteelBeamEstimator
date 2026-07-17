"""
benchmark3_export.py — Export V.TEST.3 validation artefacts.
MODEL_VERSION: 8.1.1
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import asdict
from typing import Any, Dict

from benchmark3_models import FullBenchmark3Result

_ROOT   = pathlib.Path(__file__).resolve().parents[3]
_OUTPUT = _ROOT / "Version8" / "data" / "output" / "PhaseVTEST3_generalization_validation"


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


class Benchmark3Export:

    def __init__(self, output_dir: pathlib.Path = _OUTPUT) -> None:
        self._out = output_dir
        self._out.mkdir(parents=True, exist_ok=True)

    def export_all(
        self,
        result: FullBenchmark3Result,
        statistics: Dict[str, Any],
        json_report: Dict[str, Any],
        md_report: str,
    ) -> Dict[str, pathlib.Path]:
        paths: Dict[str, pathlib.Path] = {}

        artefacts = {
            "benchmark_set3_validation.json": {
                "validation_rules": result.validation_rules,
                "overall_passed": result.overall_passed,
                "warnings": result.warnings,
                "generalization_audit": result.generalization_audit,
            },
            "benchmark_set3_statistics.json": statistics,
            "benchmark_set3_pipeline_summary.json": _safe(result.pipeline),
            "benchmark_set3_generalization_report.json": result.generalization_audit,
            "benchmark_set3_estimator_readiness.json": {
                "overall_score": result.overall_readiness_score,
                "classification": result.readiness_classification,
                "dimensions": [
                    {"dimension": s.dimension, "score": s.score, "detail": s.detail}
                    for s in result.readiness_scores
                ],
            },
            "benchmark_set3_validation_report.json": json_report,
        }

        for filename, data in artefacts.items():
            p = self._out / filename
            p.write_text(json.dumps(_safe(data), indent=2, default=str), encoding="utf-8")
            paths[filename] = p

        md_path = self._out / "benchmark_set3_validation_report.md"
        md_path.write_text(md_report, encoding="utf-8")
        paths["benchmark_set3_validation_report.md"] = md_path

        return paths
