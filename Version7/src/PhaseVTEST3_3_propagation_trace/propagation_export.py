"""
propagation_export.py — Export V.TEST.3.3 trace artefacts.
MODEL_VERSION: 8.1.4
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict

from propagation_models import PropagationTraceResult

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_OUTPUT = _ROOT / "Version7" / "data" / "output" / "PhaseVTEST3_3_propagation_trace"


class PropagationExport:

    def __init__(self, output_dir: pathlib.Path = _OUTPUT) -> None:
        self._out = output_dir
        self._out.mkdir(parents=True, exist_ok=True)

    def export_all(self, result: PropagationTraceResult, md_report: str) -> Dict[str, pathlib.Path]:
        paths: Dict[str, pathlib.Path] = {}
        artefacts = {
            "annotation_propagation_matrix.json": {
                "annotations": result.annotation_matrix,
                "count": len(result.annotation_matrix),
            },
            "engineering_bar_creation_trace.json": {
                "traces": result.engineering_bar_creation_trace,
                "count": len(result.engineering_bar_creation_trace),
            },
            "engineering_bar_filter_audit.json": {
                "filters": result.filter_audit,
            },
            "engineering_bar_statistics.json": result.statistics,
            "object_lifecycle_trace.json": {
                "lifecycles": result.lifecycle_traces,
            },
            "set3_propagation_summary.json": result.set3_summary,
            "root_cause_ranking.json": {
                "causes": result.root_cause_ranking,
                "recommendation": result.recommendation,
            },
            "propagation_validation.json": result.validation,
        }
        for name, data in artefacts.items():
            p = self._out / name
            p.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            paths[name] = p

        md = self._out / "propagation_trace_report.md"
        md.write_text(md_report, encoding="utf-8")
        paths["propagation_trace_report.md"] = md
        return paths
