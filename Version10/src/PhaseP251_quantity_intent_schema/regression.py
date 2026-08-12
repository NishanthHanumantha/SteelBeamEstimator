"""Regression fingerprints — P2.5.1 must not mutate production artefacts."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from PhaseP24_fourth_set_bar_failure_audit.regression import (
    capture_fingerprints,
    compare_fingerprints,
)


def fingerprint_paths(engine_root: Path, bundle_paths: Dict[str, Path]) -> Dict[str, Path]:
    base = Path(engine_root) / "data" / "output"
    out = dict(bundle_paths)
    out.update(
        {
            "p24_regression": base
            / "PhaseP24_fourth_set_bar_failure_audit"
            / "RegressionReport.json",
            "p250_summary": base / "PhaseP250_beam_evidence_crop_qa" / "reports" / "P250_SUMMARY.md",
            "p2503_exec": base / "PhaseP2503_accepted_owned_geometry" / "ExecutiveSummary.md",
            "p2504_exec": base
            / "PhaseP2504_accepted_owned_geometry_rendering"
            / "ExecutiveSummary.md",
        }
    )
    return out


__all__ = ["capture_fingerprints", "compare_fingerprints", "fingerprint_paths"]
