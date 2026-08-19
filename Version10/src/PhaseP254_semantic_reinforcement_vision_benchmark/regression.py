"""Regression fingerprints for P2.5.4 — upstream including P2.5.3 must remain unchanged."""
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
            "p2521_status": base
            / "PhaseP2521_crop_readability_refinement"
            / "P2.5.2.1_STATUS.md",
            "p2522_status": base
            / "PhaseP2522_render_safe_annotation_bounds"
            / "P2.5.2.2_STATUS.md",
            "p2523_status": base
            / "PhaseP2523_target_beam_visual_completeness"
            / "P2.5.2.3_STATUS.md",
            "p2523_manifest": base
            / "PhaseP2523_target_beam_visual_completeness"
            / "manifests"
            / "TargetBeamCompletenessManifest.json",
            "p253_status": base
            / "PhaseP253_claude_vision_interpretation_pilot"
            / "P2.5.3_STATUS.md",
            "p253_summary": base
            / "PhaseP253_claude_vision_interpretation_pilot"
            / "pilot_summary.json",
        }
    )
    return out


PRODUCTION_MODULE_PREFIXES = (
    "PhaseSI",
    "PhaseT16",
    "PhaseT17",
    "PhaseT18",
    "PhaseR31",
    "PhaseVB1",
    "excel",
    "bbs",
)


def firewall_check(version10_root: Path) -> Dict[str, Any]:
    """ShadowResolverResult must not be imported by production engineering modules."""
    src = Path(version10_root) / "src"
    offenders = []
    for path in src.rglob("*.py"):
        rel = str(path.relative_to(src)).replace("\\", "/")
        if any(x in rel for x in ("PhaseP254_", "PhaseP255_", "PhaseP256_", "PhaseP257_", "PhaseP258_", "PhaseP259_", "PhaseP2510_", "PhaseP2511_", "PhaseP26_", "PhaseP261_", "PhaseP262_", "PhaseP263_", "PhaseP264_", "PhaseP265_", "PhaseP266_", "PhaseP267_", "PhaseP268_", "PhaseP269_", "PhaseP2610A_", "PhaseP2610B_")):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "PhaseP254_semantic_reinforcement_vision_benchmark" in text or "ShadowResolverResult" in text:
            offenders.append(rel)
    return {
        "ok": len(offenders) == 0,
        "offenders": offenders,
        "shadow_writes_production": False,
        "note": "P2.5.4 runner writes only benchmark/shadow/evaluation artefacts",
    }


__all__ = ["capture_fingerprints", "compare_fingerprints", "fingerprint_paths", "firewall_check"]
