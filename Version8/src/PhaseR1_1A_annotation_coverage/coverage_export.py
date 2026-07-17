"""
coverage_export.py — Phase R.1.1A consolidated export (11 artefacts).
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict


def _json(obj: object) -> str:
    return json.dumps(obj, indent=2, default=str, ensure_ascii=False)


class CoverageExport:

    def __init__(self, project_root: pathlib.Path):
        self._out_dir = project_root / "data/output/PhaseR1_1A_annotation_coverage"
        self._out_dir.mkdir(parents=True, exist_ok=True)

    def export_all(self, result: Dict[str, Any], report_md: str) -> Dict[str, str]:
        written: Dict[str, str] = {}
        payloads = {
            "annotation_recovery_summary.json": result.get("recovery_summary", {}),
            "coverage_statistics.json": result.get("coverage_statistics", {}),
            "benchmark_regression_summary.json": result.get("regression", {}),
            "annotation_discovery_validation.json": result.get("validation", {}),
        }
        for name, data in payloads.items():
            path = self._out_dir / name
            path.write_text(_json(data), encoding="utf-8")
            written[name] = str(path)

        report_path = self._out_dir / "annotation_coverage_report.md"
        report_path.write_text(report_md, encoding="utf-8")
        written["annotation_coverage_report.md"] = str(report_path)

        r1a_dir = self._out_dir
        for name in (
            "beam_detail_clusters.json",
            "adaptive_search_regions.json",
            "annotation_association_scores.json",
            "orphan_annotation_recovery.json",
            "beam_annotation_coverage.json",
            "engineering_confidence_summary.json",
        ):
            src = r1a_dir / name
            if src.exists():
                written[name] = str(src)

        return written
