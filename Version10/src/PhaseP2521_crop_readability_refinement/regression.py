"""Regression fingerprints for P2.5.2.1 — must not mutate upstream phases."""
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
            "p251_report": base
            / "PhaseP251_quantity_intent_schema"
            / "P2.5.1_QuantityIntent_Report.md",
            "p252_status": base
            / "PhaseP252_vision_candidate_set"
            / "ExecutiveSummary.md",
            "p252_manifest": base
            / "PhaseP252_vision_candidate_set"
            / "manifests"
            / "VisionCandidateManifest.json",
            "p252_golden": base
            / "PhaseP252_vision_candidate_set"
            / "golden_results.json",
            "p252_metrics": base
            / "PhaseP252_vision_candidate_set"
            / "metrics"
            / "metrics.json",
            "p2504_exec": base
            / "PhaseP2504_accepted_owned_geometry_rendering"
            / "ExecutiveSummary.md",
            "p2503_exec": base / "PhaseP2503_accepted_owned_geometry" / "ExecutiveSummary.md",
        }
    )
    return out


__all__ = ["capture_fingerprints", "compare_fingerprints", "fingerprint_paths"]
