"""Regression fingerprints for P2.5.2.3."""
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
            "p252_manifest": base
            / "PhaseP252_vision_candidate_set"
            / "manifests"
            / "VisionCandidateManifest.json",
            "p252_metrics": base
            / "PhaseP252_vision_candidate_set"
            / "metrics"
            / "metrics.json",
            "p2522_status": base
            / "PhaseP2522_render_safe_annotation_bounds"
            / "P2.5.2.2_STATUS.md",
            "p2522_manifest": base
            / "PhaseP2522_render_safe_annotation_bounds"
            / "manifests"
            / "RenderSafeEvidenceManifest.json",
            "p2521_status": base
            / "PhaseP2521_crop_readability_refinement"
            / "P2.5.2.1_STATUS.md",
        }
    )
    return out


__all__ = ["capture_fingerprints", "compare_fingerprints", "fingerprint_paths"]
