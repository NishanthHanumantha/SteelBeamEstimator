"""
runtime_cache_detector.py — Identifies stale output artefacts whose timestamps
predate the V.ROOT.1 adapter files.
MODEL_VERSION: 7.1.3  |  READ-ONLY
"""

from __future__ import annotations
import json
import pathlib
from datetime import datetime, timezone
from typing import Dict, List

WORKSPACE = pathlib.Path(r"C:\Users\nishanth.h\SteelBeamEstimator")

_V7_OUTPUT = WORKSPACE / "Version7/data/output"

# All pipeline stage output directories to scan for stale artefacts
_STAGE_DIRS = {
    "L2":  _V7_OUTPUT / "PhaseL.2 - engineering_reinforcement_interpretation",
    "SI0": _V7_OUTPUT / "PhaseSI.0_stirrup_recovery",
    "SI1": _V7_OUTPUT / "PhaseSI.1_stirrup_improvement",
    "L22": _V7_OUTPUT / "PhaseL.2.2_geometry_recovery",
    "L21": _V7_OUTPUT / "PhaseL.2.1 - engineering_feature_extraction",
    "L3":  _V7_OUTPUT / "PhaseL.3_beam_pattern_recognition",
    "VB1": _V7_OUTPUT / "Production_Output",
}

_ADAPTER_PATHS = [
    WORKSPACE / "Version5/data/output/phase_g/g_5_1_engineering_objects/engineering_objects.json",
    WORKSPACE / "Version5/data/output/phase_i/i_15_beam_schedule/beam_schedule_results.json",
]


def _mtime(p: pathlib.Path) -> float:
    try:
        return p.stat().st_mtime
    except Exception:
        return 0.0


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat() if epoch else "N/A"


class RuntimeCacheDetector:

    def detect(self) -> dict:
        # Get the latest adapter file modification time
        adapter_mtime = max((_mtime(p) for p in _ADAPTER_PATHS), default=0.0)
        adapter_iso   = _iso(adapter_mtime)

        stale: List[dict] = []
        current: List[dict] = []

        for stage_id, stage_dir in _STAGE_DIRS.items():
            if not stage_dir.exists():
                continue
            for json_file in sorted(stage_dir.glob("*.json")):
                file_mtime = _mtime(json_file)
                is_stale   = file_mtime < adapter_mtime
                entry = {
                    "stage":       stage_id,
                    "file":        json_file.name,
                    "absolute_path": str(json_file),
                    "mtime_iso":   _iso(file_mtime),
                    "mtime_epoch": file_mtime,
                    "adapter_mtime_iso": adapter_iso,
                    "is_stale":    is_stale,
                    "age_vs_adapter_s": round(adapter_mtime - file_mtime, 1),
                }
                (stale if is_stale else current).append(entry)

        stale_stages = sorted({e["stage"] for e in stale})

        return {
            "adapter_write_time_iso":   adapter_iso,
            "total_output_files":       len(stale) + len(current),
            "stale_files":              len(stale),
            "current_files":            len(current),
            "stale_stages":             stale_stages,
            "stale_details":            stale,
            "current_details":          current,
            "summary": (
                f"{len(stale)} output file(s) across stages {stale_stages} "
                f"were generated BEFORE V.ROOT.1 updated the adapter files "
                f"(adapter written at {adapter_iso}). These are STALE."
                if stale
                else "All output files are newer than the adapter files."
            ),
        }
