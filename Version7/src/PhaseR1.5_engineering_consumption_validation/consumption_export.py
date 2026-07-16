"""Export R.1.5 consumption validation artefacts."""
from __future__ import annotations
import json
import pathlib
from typing import Any, Dict, List


class ConsumptionExport:

    def __init__(self, output_dir: pathlib.Path):
        self._out = output_dir
        self._out.mkdir(parents=True, exist_ok=True)

    def export_all(
        self,
        traces: List[Any],
        steel_traces: Dict[str, Any],
        bbs_traces: Dict[str, Any],
        dia_trace: Dict[str, Any],
        beam_trace: Dict[str, Any],
        project_trace: Dict[str, Any],
        excel_trace: Dict[str, Any],
        qty_validation: Dict[str, Any],
        stats: Dict[str, Any],
        matrix: List[Any],
        root_causes: Dict[str, Any],
        validation: Any,
        summary: Dict[str, Any],
        markdown: str,
    ) -> Dict[str, str]:
        exports = {
            "engineering_bar_trace.json": {
                "total": len(traces),
                "bars": [t.to_dict() for t in traces],
            },
            "steel_weight_trace.json": {
                k: v.to_dict() for k, v in steel_traces.items()
            },
            "bbs_trace.json": {
                k: v.to_dict() for k, v in bbs_traces.items()
            },
            "diameter_summary_trace.json": dia_trace,
            "beam_total_trace.json": beam_trace,
            "project_total_trace.json": project_trace,
            "excel_trace.json": excel_trace,
            "quantity_validation.json": qty_validation,
            "consumption_statistics.json": stats,
            "consumption_matrix.json": {
                "rows": [m.to_dict() for m in matrix],
                "total": len(matrix),
            },
            "root_cause_report.json": root_causes,
            "engineering_consumption_report.json": {
                "summary": summary,
                "validation": validation.to_dict(),
            },
        }

        paths: Dict[str, str] = {}
        for name, data in exports.items():
            path = self._out / name
            path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            paths[name] = str(path)

        md_path = self._out / "engineering_consumption_report.md"
        md_path.write_text(markdown, encoding="utf-8")
        paths["engineering_consumption_report.md"] = str(md_path)

        return paths
