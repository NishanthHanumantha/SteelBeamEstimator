"""Export artefacts for Phase R.1.3."""
from __future__ import annotations
import json
import pathlib
from typing import Any, Dict


class IntegrationExport:

    def __init__(self, output_dir: pathlib.Path):
        self._out = output_dir
        self._out.mkdir(parents=True, exist_ok=True)

    def export_all(
        self,
        summary: Dict[str, Any],
        validation: Dict[str, Any],
        statistics: Dict[str, Any],
        comparison: Dict[str, Any],
        source_report: Dict[str, Any],
        propagation_matrix: list,
        dependency_graph: Dict[str, Any],
        engineering_md: str,
    ) -> Dict[str, str]:
        exports = {
            "pipeline_dependency_graph.json": dependency_graph,
            "beam_propagation_matrix.json": {
                "beams": propagation_matrix,
                "total": len(propagation_matrix),
            },
            "reinforcement_source_report.json": source_report,
            "engineering_bar_statistics.json": statistics.get(
                "engineering_bar_counts", statistics
            ),
            "production_pipeline_report.json": {
                "source": source_report,
                "comparison": comparison,
                "after": statistics.get("after", {}),
            },
            "integration_validation.json": validation,
            "integration_summary.json": summary,
            "engineering_validation_report.json": {
                "validation": validation,
                "statistics": statistics,
                "comparison": comparison,
            },
        }

        paths: Dict[str, str] = {}
        for filename, data in exports.items():
            path = self._out / filename
            path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            paths[filename] = str(path)

        md_path = self._out / "engineering_validation_report.md"
        md_path.write_text(engineering_md, encoding="utf-8")
        paths["engineering_validation_report.md"] = str(md_path)

        return paths
