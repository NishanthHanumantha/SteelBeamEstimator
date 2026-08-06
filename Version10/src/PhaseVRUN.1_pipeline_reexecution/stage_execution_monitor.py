"""
stage_execution_monitor.py — Validates each stage's output after execution.
MODEL_VERSION: 7.2.0
"""

from __future__ import annotations
import json
import pathlib
from datetime import datetime, timezone
from typing import List, Optional

WORKSPACE = pathlib.Path(r"C:\Users\nishanth.h\SteelBeamEstimator")
V7        = WORKSPACE / "Version8"


def _mtime(p: pathlib.Path) -> float:
    try:
        return p.stat().st_mtime
    except Exception:
        return 0.0


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat() if epoch else "N/A"


class StageExecutionMonitor:
    """After each stage, checks that expected output files exist and are fresh."""

    def verify(
        self,
        stage_id:       str,
        output_dir_rel: str,
        expected_files: List[str],
        run_start_epoch: float,
    ) -> dict:
        out_dir = V7 / output_dir_rel
        checks  = []
        all_ok  = True

        # Check directory exists
        if not out_dir.exists():
            return {
                "stage_id": stage_id,
                "status":   "FAIL",
                "checks":   [{"name": "output_dir_exists", "status": "FAIL",
                               "detail": f"{out_dir} does not exist"}],
            }

        actual_files = {f.name: f for f in out_dir.glob("*") if f.is_file()}

        for fname in expected_files:
            p = out_dir / fname
            if p.name in actual_files:
                mt = _mtime(p)
                fresh = mt >= run_start_epoch
                checks.append({
                    "name":   fname,
                    "status": "PASS" if fresh else "STALE",
                    "mtime":  _iso(mt),
                    "fresh":  fresh,
                })
                if not fresh:
                    all_ok = False
            else:
                checks.append({"name": fname, "status": "MISSING", "fresh": False})
                all_ok = False

        # Extra freshness: all files in the dir should be newer than run_start
        total   = len(actual_files)
        fresh_n = sum(1 for f in actual_files.values() if _mtime(f) >= run_start_epoch)

        return {
            "stage_id":       stage_id,
            "status":         "PASS" if all_ok else "FAIL",
            "output_dir":     str(out_dir),
            "checks":         checks,
            "total_files":    total,
            "fresh_files":    fresh_n,
            "stale_files":    total - fresh_n,
        }
