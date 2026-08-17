"""
Evaluation-only artefact paths (estimator workbooks).

MUST NOT be imported by sampler / Vision observation / region builder.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from .config import SET_KEYS

# Filenames live here so runtime modules never mention estimator workbooks.
SET_ESTIMATOR_REL = {
    "Fourth": (
        "Fourth Set Drawings",
        "Estimator_Output_4thSet",
        "EstimatorOutput_Basement_Beam BBS_INIZIO.xlsx",
    ),
    "Fifth": (
        "Fifth Set Drawings",
        "Estimator_Output_5thSet",
        "EstimatorOutput_9TH FLOOR.xlsx",
    ),
    "Sixth": (
        "Sixth Set Drawings",
        "Estimator_Output_6thSet",
        "Estimator_Output_11-18TH FLOOR.xlsx",
    ),
}


def estimator_excel_path(version10_root: Path, set_key: str) -> Path:
    rel = SET_ESTIMATOR_REL[set_key]
    return Path(version10_root).parent / "Test_Input" / rel[0] / rel[1] / rel[2]


def estimator_fingerprint_paths(version10_root: Path) -> Dict[str, Path]:
    return {
        f"{key.lower()}_estimator_excel": estimator_excel_path(version10_root, key)
        for key in SET_KEYS
        if key in SET_ESTIMATOR_REL
    }


__all__ = [
    "SET_ESTIMATOR_REL",
    "estimator_excel_path",
    "estimator_fingerprint_paths",
]
