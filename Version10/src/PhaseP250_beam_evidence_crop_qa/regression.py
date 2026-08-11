"""
Regression fingerprints for P2.5.0 (reuse P2.4 helpers).
MODEL_VERSION: 10.6.0
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from PhaseP24_fourth_set_bar_failure_audit.regression import (
    capture_fingerprints,
    compare_fingerprints,
    sha256_file,
)

MODEL_VERSION = "10.6.0"


def fingerprint_paths(bundle_paths: Dict[str, Path], engine_root: Path) -> Dict[str, Path]:
    out = dict(bundle_paths)
    base = Path(engine_root) / "data" / "output"
    out.update(
        {
            "p22_regression": base / "PhaseP22_leader_chain_evidence" / "P22_regression.json",
            "p23_regression": base / "PhaseP23_controlled_production_gate" / "RegressionReport.json",
            "p231_regression": base
            / "PhaseP23_1_controlled_engineering_recompute"
            / "RegressionReport.json",
            "p24_regression": base / "PhaseP24_fourth_set_bar_failure_audit" / "RegressionReport.json",
        }
    )
    return out


__all__ = [
    "capture_fingerprints",
    "compare_fingerprints",
    "sha256_file",
    "fingerprint_paths",
]
