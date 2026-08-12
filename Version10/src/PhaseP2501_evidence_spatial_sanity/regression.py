"""Regression fingerprints — must not mutate P2.4 / production artefacts."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from PhaseP24_fourth_set_bar_failure_audit.regression import (
    capture_fingerprints,
    compare_fingerprints,
)


def fingerprint_paths(engine_root: Path, bundle_paths: Dict[str, Path]) -> Dict[str, Path]:
    base = Path(engine_root) / "data" / "output"
    out = dict(bundle_paths)
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


__all__ = ["capture_fingerprints", "compare_fingerprints", "fingerprint_paths"]
