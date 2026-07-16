"""Export Phase R.1.4 validation artefacts."""
from __future__ import annotations
import json
import pathlib
from typing import Any, Dict

from .validation_models import ValidationResult


class ValidationExport:

    def __init__(self, output_dir: pathlib.Path):
        self._out = output_dir
        self._out.mkdir(parents=True, exist_ok=True)

    def export_all(
        self,
        result: ValidationResult,
        engineering_summary: Dict[str, Any],
        markdown_report: str,
    ) -> Dict[str, str]:
        paths: Dict[str, str] = {}

        exports = {
            "integrity_validation.json": result.to_dict(),
            "coverage_statistics.json": result.coverage,
            "beam_status_matrix.json": {
                "beams": result.beam_status_matrix,
                "total": len(result.beam_status_matrix),
            },
            "pipeline_health.json": {
                "pipeline_health_score": result.pipeline_health_score,
                "integrity_score": result.integrity_score,
                "coverage_pct": result.coverage.get("coverage_pct", 0),
                "propagation_pct": result.coverage.get("propagation_pct", 0),
            },
            "quality_gate.json": result.quality_gate,
            "engineering_summary.json": engineering_summary,
            "validation_report.json": {
                "rules": {k: v.to_dict() for k, v in result.rules.items()},
                "quality_gate_status": result.quality_gate_status,
                "production_allowed": result.production_allowed,
                "engineering_summary": engineering_summary,
            },
        }

        for filename, data in exports.items():
            path = self._out / filename
            path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            paths[filename] = str(path)

        md_path = self._out / "validation_report.md"
        md_path.write_text(markdown_report, encoding="utf-8")
        paths["validation_report.md"] = str(md_path)

        return paths
