"""Regression fingerprints — P2.5.0.3 must not mutate engineering artefacts."""
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
            "p24_regression": base
            / "PhaseP24_fourth_set_bar_failure_audit"
            / "RegressionReport.json",
            "p250_summary": base / "PhaseP250_beam_evidence_crop_qa" / "reports" / "P250_SUMMARY.md",
            "p2501_exec": base / "PhaseP2501_evidence_spatial_sanity" / "ExecutiveSummary.md",
            "p2502_exec": base / "PhaseP2502_top_reinforcement_trace" / "ExecutiveSummary.md",
        }
    )
    return out


__all__ = ["capture_fingerprints", "compare_fingerprints", "fingerprint_paths"]
