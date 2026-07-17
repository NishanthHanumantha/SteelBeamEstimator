"""
Phase V.ROOT.1 -- initialization_export.py
Export 8 JSON artefacts for Phase V.ROOT.1.
MODEL_VERSION: 7.1.0
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List

_ROOT   = pathlib.Path(__file__).resolve().parents[3]
_V7     = _ROOT / "Version8"
_OUTPUT = _V7   / "data/output/PhaseVROOT.1_dynamic_pipeline_initialization"


class InitializationExport:
    """Export all V.ROOT.1 artefacts to JSON."""

    def __init__(self, output_dir: pathlib.Path = _OUTPUT) -> None:
        self._out = output_dir
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
             "Canonical beam registry from DXF discovery"),
            ("engineering_objects.json",        eng_obj_result.get('payloads', {}).get(
                'engineering_objects', {}),
             "Engineering objects generated from DXF"),
            ("pipeline_context.json",           pipeline_context,
             "Complete pipeline context for downstream phases"),
            ("dependency_analysis.json",        dep_check,
             "Version5 and Benchmark Set 1 dependency analysis"),
            ("initialization_statistics.json",  stats,
             "Initialization timing and counts"),
            ("initialization_report.json",      report,
             "Complete 8-section initialization report"),
        ]

        export_status = []
        for filename, data, desc in artefacts:
            path = self._out / filename
            try:
                path.write_text(
                    json.dumps(data, indent=2, default=str),
                    encoding='utf-8'
                )
                export_status.append({
                    'file':   filename,
                    'status': 'OK',
                    'path':   str(path),
                    'description': desc,
                })
                print(f"  [OK]  {filename}")
            except Exception as exc:
                export_status.append({
                    'file':   filename,
                    'status': 'FAIL',
                    'error':  str(exc),
                })
                print(f"  [FAIL] {filename}: {exc}")

        return export_status

    def validate_exports(self, export_status: List[Dict[str, Any]]) -> Dict[str, Any]:
        passed = sum(1 for e in export_status if e['status'] == 'OK')
        return {
            'status':  'PASS' if passed == len(export_status) else 'PARTIAL',
            'total':   len(export_status),
            'passed':  passed,
            'failed':  len(export_status) - passed,
            'output_dir': str(self._out),
            'files':   export_status,
        }
