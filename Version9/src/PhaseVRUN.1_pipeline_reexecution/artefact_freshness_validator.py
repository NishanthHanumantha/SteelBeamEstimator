"""
artefact_freshness_validator.py — Validates all artefacts are newer than adapter files.
MODEL_VERSION: 7.2.0
"""

from __future__ import annotations
import pathlib
from datetime import datetime, timezone
from typing import Dict, List

WORKSPACE = pathlib.Path(r"C:\Users\nishanth.h\SteelBeamEstimator")
V7        = WORKSPACE / "Version8"

ADAPTER_FILES = [
    WORKSPACE / "Version5/data/output/phase_i/i_15_beam_schedule/beam_schedule_results.json",
    WORKSPACE / "Version5/data/output/phase_g/g_5_1_engineering_objects/engineering_objects.json",
]

STAGE_DIRS = {
    "VROOT1": V7 / "data/output/PhaseVROOT.1_dynamic_pipeline_initialization",
    "L2":     V7 / "data/output/PhaseL.2 - engineering_reinforcement_interpretation",
    "SI0":    V7 / "data/output/PhaseSI.0_stirrup_recovery",
    "SI1":    V7 / "data/output/PhaseSI.1_stirrup_improvement",
    "L22":    V7 / "data/output/PhaseL.2.2_geometry_recovery",
    "L21":    V7 / "data/output/PhaseL.2.1 - engineering_feature_extraction",
    "L3":     V7 / "data/output/PhaseL.3_beam_pattern_recognition",
    "VB1":    V7 / "data/output/Production_Output",
}


def _mtime(p: pathlib.Path) -> float:
    try:
        return p.stat().st_mtime
    except Exception:
        return 0.0


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat() if epoch else "N/A"


class ArtefactFreshnessValidator:

    def validate(self, run_start_epoch: float) -> dict:
        adapter_mtime = max((_mtime(p) for p in ADAPTER_FILES), default=0.0)
        adapter_iso   = _iso(adapter_mtime)
        run_start_iso = _iso(run_start_epoch)

        stage_results = []
        total_stale = 0
        total_fresh = 0

        for stage_id, stage_dir in STAGE_DIRS.items():
            if not stage_dir.exists():
                continue
            files = list(stage_dir.glob("*.json")) + list(stage_dir.glob("*.xlsx"))
            for f in files:
                mt    = _mtime(f)
                fresh = mt >= run_start_epoch
                total_fresh += int(fresh)
                total_stale += int(not fresh)
                stage_results.append({
                    "stage_id":   stage_id,
                    "file":       f.name,
                    "mtime_iso":  _iso(mt),
                    "fresh":      fresh,
                    "newer_than_adapter": mt > adapter_mtime,
                })

        passed = all(r["fresh"] for r in stage_results)
        return {
            "adapter_write_time_iso":  adapter_iso,
            "run_start_iso":           run_start_iso,
            "total_artefacts_checked": len(stage_results),
            "fresh_artefacts":         total_fresh,
            "stale_artefacts":         total_stale,
            "overall_status":          "PASS" if passed else "FAIL",
            "details":                 stage_results,
        }
