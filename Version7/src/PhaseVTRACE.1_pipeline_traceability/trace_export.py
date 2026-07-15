"""
trace_export.py — Exports all 9 traceability artefacts.
MODEL_VERSION: 7.1.2  |  READ-ONLY (writes only to the designated output folder)
"""

from __future__ import annotations
import json
import pathlib
from typing import Dict, List

from .engineering_trace_models import (
    BeamLifecycle, DuplicateRecord, LostBeam, RootCause, StageSnapshot, TraceStatistics
)

OUTPUT_DIR = pathlib.Path(
    r"C:\Users\nishanth.h\SteelBeamEstimator\Version7\data\output"
    r"\PhaseVTRACE.1_pipeline_traceability"
)


def _dump(name: str, data: object) -> pathlib.Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / name
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


class TraceExporter:

    def export_all(
        self,
        snapshots:        Dict[str, StageSnapshot],
        lifecycles:       Dict[str, BeamLifecycle],
        lost_beams:       List[LostBeam],
        duplicates:       List[DuplicateRecord],
        root_causes:      List[RootCause],
        flow:             dict,
        statistics:       TraceStatistics,
        validation:       List[dict],
        lifecycle_matrix: dict,
        report:           dict,
    ) -> Dict[str, str]:
        results = {}

        artefacts = {
            "pipeline_stage_snapshots.json": {
                sid: snap.to_dict() for sid, snap in snapshots.items()
            },
            "beam_lifecycle_matrix.json": {
                "total_beams":    len(lifecycle_matrix),
                "stage_columns":  list(next(iter(lifecycle_matrix.values()), {}).keys()),
                "matrix":         lifecycle_matrix,
                "lifecycle_details": {
                    bid: lc.to_dict() for bid, lc in lifecycles.items()
                },
            },
            "beam_loss_report.json": {
                "total_lost":  len(lost_beams),
                "lost_beams":  [lb.to_dict() for lb in lost_beams],
            },
            "beam_duplication_report.json": {
                "total_records": len(duplicates),
                "records":       [d.to_dict() for d in duplicates],
            },
            "pipeline_flow_report.json": flow,
            "root_cause_report.json": {
                "total_root_causes": len(root_causes),
                "root_causes":       [rc.to_dict() for rc in root_causes],
            },
            "trace_statistics.json":        statistics.to_dict(),
            "trace_validation_report.json": {
                "rules":   validation,
                "passed":  sum(1 for v in validation if v.get("status") == "PASS"),
                "failed":  sum(1 for v in validation if v.get("status") == "FAIL"),
                "warned":  sum(1 for v in validation if v.get("status") == "WARN"),
            },
            "engineering_trace_report.json": report,
        }

        for filename, data in artefacts.items():
            path = _dump(filename, data)
            results[filename] = str(path)
            print(f"  [OK]  {filename}")

        return results
