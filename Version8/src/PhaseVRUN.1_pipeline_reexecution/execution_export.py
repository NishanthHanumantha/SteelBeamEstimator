"""
execution_export.py — Exports all V.RUN.1 artefacts.
MODEL_VERSION: 7.2.0
"""

from __future__ import annotations
import json
import pathlib
from typing import Any, Dict

OUTPUT_DIR = pathlib.Path(
    r"C:\Users\nishanth.h\SteelBeamEstimator\Version8\data\output"
    r"\PhaseVRUN.1_pipeline_reexecution"
)


def _dump(name: str, data: Any) -> pathlib.Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / name
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


class ExecutionExporter:

    def export_all(
        self,
        stage_results,
        propagation,
        freshness,
        statistics,
        validation,
        report,
        stale_archives,
    ) -> Dict[str, str]:
        exported = {}

        artefacts = {
            "pipeline_execution_report.json":   report,
            "stage_execution_report.json": {
                "stages": [s.to_dict() for s in stage_results],
            },
            "artefact_freshness_report.json":   freshness,
            "beam_count_propagation.json": {
                "propagation": propagation,
            },
            "execution_statistics.json":        statistics,
            "production_execution_summary.json": {
                "overall_status":       report.get("sections", {}).get("1_executive_summary", {}),
                "production_readiness": report.get("sections", {}).get("9_production_readiness", {}),
                "remaining_issues":     report.get("sections", {}).get("8_remaining_issues", []),
                "stale_archives":       [a.__dict__ for a in stale_archives],
            },
        }

        for filename, data in artefacts.items():
            path = _dump(filename, data)
            exported[filename] = str(path)
            print(f"  [OK]  {filename}")

        return exported
