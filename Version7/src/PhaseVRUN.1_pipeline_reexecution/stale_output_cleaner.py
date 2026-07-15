"""
stale_output_cleaner.py — Archives stale downstream output files before fresh run.
MODEL_VERSION: 7.2.0

Archives but does NOT remove V.ROOT.1 outputs, Benchmark inputs, or config files.
"""

from __future__ import annotations
import pathlib
import shutil
from datetime import datetime, timezone
from typing import List
from .pipeline_execution_models import StaleArchiveRecord

WORKSPACE   = pathlib.Path(r"C:\Users\nishanth.h\SteelBeamEstimator")
V7          = WORKSPACE / "Version7"
ARCHIVE_ROOT = V7 / "data/output/_stale_archive_vrun1"

STALE_DIRS = {
    "L2":  V7 / "data/output/PhaseL.2 - engineering_reinforcement_interpretation",
    "SI0": V7 / "data/output/PhaseSI.0_stirrup_recovery",
    "SI1": V7 / "data/output/PhaseSI.1_stirrup_improvement",
    "L22": V7 / "data/output/PhaseL.2.2_geometry_recovery",
    "L21": V7 / "data/output/PhaseL.2.1 - engineering_feature_extraction",
    "L3":  V7 / "data/output/PhaseL.3_beam_pattern_recognition",
    "VB1": V7 / "data/output/Production_Output",
}


class StaleOutputCleaner:

    def archive_all(self) -> List[StaleArchiveRecord]:
        ts  = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        records: List[StaleArchiveRecord] = []
        ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)

        for stage_id, src_dir in STALE_DIRS.items():
            if not src_dir.exists():
                print(f"  [SKIP] {stage_id}: directory not found.")
                continue

            dest = ARCHIVE_ROOT / f"{ts}_{stage_id}"
            dest.mkdir(parents=True, exist_ok=True)

            files = list(src_dir.glob("*"))
            count = 0
            for f in files:
                if f.is_file():
                    shutil.copy2(str(f), str(dest / f.name))
                    f.unlink()
                    count += 1

            record = StaleArchiveRecord(
                stage_id    = stage_id,
                source_path = str(src_dir),
                archive_path = str(dest),
                file_count   = count,
                archived_at  = ts,
            )
            records.append(record)
            print(f"  [ARCHIVED] {stage_id}: {count} files → {dest.name}")

        return records
