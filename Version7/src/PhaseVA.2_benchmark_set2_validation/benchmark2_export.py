"""
Phase V.A.2 -- benchmark2_export.py
Export 7 JSON artefacts for Benchmark Set 2 validation.
MODEL_VERSION: 7.0.0
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from benchmark2_models import (
    Benchmark2Manifest,
    BenchmarkSetComparison,
    EngineeringKPIs,
    FullBenchmark2Result,
    PipelineRunResult,
    WorkbookComparison,
    WorkbookValidation,
)

_ROOT   = pathlib.Path(__file__).resolve().parents[3]
_V7     = _ROOT / "Version7"
_OUTPUT = _V7   / "data/output/PhaseVA.2_benchmark_set2_validation"


def _json_safe(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _json_safe(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, pathlib.Path):
        return str(obj)
    return obj


class Benchmark2Export:
    """Export all V.A.2 validation artefacts to JSON files."""

    def __init__(self, output_dir: pathlib.Path = _OUTPUT) -> None:
        self._out = output_dir
        self._out.mkdir(parents=True, exist_ok=True)

    def export_all(
        self,
        full_report:     Dict[str, Any],
        result:          FullBenchmark2Result,
        stats:           Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        artefacts = [
            {
                "filename": "benchmark_set2_validation_report.json",
                "data": full_report,
                "description": "Complete 10-section V.A.2 validation report",
            },
            {
                "filename": "benchmark_set2_engineering_summary.json",
                "data": _json_safe(result.engineering_kpis),
                "description": "Engineering KPIs for Benchmark Set 2",
            },
            {
                "filename": "benchmark_set2_workbook_comparison.json",
                "data": _json_safe(result.workbook_comparison),
                "description": "Workbook comparison result (generated vs estimator reference)",
            },
            {
                "filename": "benchmark_set1_vs_set2_comparison.json",
                "data": _json_safe(result.set_comparison),
                "description": "Benchmark Set 1 vs Set 2 metric comparison",
            },
            {
                "filename": "benchmark_set2_statistics.json",
                "data": stats,
                "description": "Aggregated pipeline, engineering, workbook, and comparison statistics",
            },
            {
                "filename": "generalization_report.json",
                "data": result.generalization_assessment or {},
                "description": "Generalization assessment and classification",
            },
            {
                "filename": "benchmark2_manifest.json",
                "data": _json_safe(result.manifest),
                "description": "Benchmark Set 2 input file manifest",
            },
        ]

        export_status = []
        for a in artefacts:
            path = self._out / a["filename"]
            try:
                path.write_text(json.dumps(a["data"], indent=2, default=str), encoding="utf-8")
                export_status.append({"file": a["filename"], "status": "OK", "path": str(path)})
                print(f"  [OK]  Exported -> {a['filename']}")
            except Exception as exc:
                export_status.append({"file": a["filename"], "status": "FAIL", "error": str(exc)})
                print(f"  [FAIL] {a['filename']}: {exc}")

        return export_status

    def validate_exports(self, export_status: List[Dict[str, Any]]) -> Dict[str, Any]:
        passed = sum(1 for e in export_status if e["status"] == "OK")
        return {
            "status": "PASS" if passed == len(export_status) else "PARTIAL",
            "total": len(export_status),
            "passed": passed,
            "failed": len(export_status) - passed,
            "files": export_status,
        }
