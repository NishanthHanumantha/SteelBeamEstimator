"""
Phase V.ROOT.1 -- initialization_export.py
Export 8 JSON artefacts for Phase V.ROOT.1.
MODEL_VERSION: 8.9.0
"""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any, Dict, List, Optional

# Allow import of run_context when cwd/sys.path is Version10 or PhaseVROOT1 src
_SRC = pathlib.Path(__file__).resolve().parents[1]  # Version10/src
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config.run_context import PHASE_VROOT1, resolve_run_context  # noqa: E402


def _default_output_dir() -> pathlib.Path:
    ctx = resolve_run_context()
    return ctx.artefact(PHASE_VROOT1)


class InitializationExport:
    """Export all V.ROOT.1 artefacts to JSON."""

    def __init__(self, output_dir: Optional[pathlib.Path] = None) -> None:
        self._out = pathlib.Path(output_dir) if output_dir else _default_output_dir()
        self._out.mkdir(parents=True, exist_ok=True)

    def export_all(
        self,
        project_manifest:  Dict[str, Any],
        drawing_manifest:  Dict[str, Any],
        beam_registry:     Dict[str, Any],
        eng_obj_result:    Dict[str, Any],
        pipeline_context:  Dict[str, Any],
        dep_check:         Dict[str, Any],
        stats:             Dict[str, Any],
        report:            Dict[str, Any],
    ) -> List[Dict[str, Any]]:

        artefacts = [
            ("project_manifest.json",          project_manifest,
             "Dynamically discovered project identity"),
            ("drawing_manifest.json",           drawing_manifest,
             "All DXF drawings discovered and classified"),
            ("beam_registry.json",              beam_registry,
             "Dynamically discovered beam schedule"),
            ("engineering_objects.json",        eng_obj_result,
             "Initialized engineering object collection"),
            ("pipeline_context.json",           pipeline_context,
             "Downstream pipeline configuration"),
            ("dependency_analysis.json",        dep_check,
             "Version5 and Benchmark Set 1 dependency analysis"),
            ("initialization_statistics.json",  stats,
             "Initialization performance and coverage stats"),
            ("initialization_report.json",      report,
             "Full V.ROOT.1 initialization report"),
        ]

        status: List[Dict[str, Any]] = []
        for filename, payload, description in artefacts:
            path = self._out / filename
            path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
            status.append({
                "file": filename,
                "path": str(path),
                "description": description,
                "ok": path.exists(),
            })
        return status

    def validate_exports(self, export_status: List[Dict[str, Any]]) -> Dict[str, Any]:
        passed = sum(1 for e in export_status if e.get("ok"))
        return {
            "passed": passed,
            "total": len(export_status),
            "output_dir": str(self._out),
            "files": export_status,
        }
