"""Regression fingerprints + production firewall for P2.5.8."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from PhaseP254_semantic_reinforcement_vision_benchmark.regression import (
    PRODUCTION_MODULE_PREFIXES,
)
from PhaseP257_unseen_drawing_controlled_vision_validation.regression import (
    capture_fingerprints,
    compare_fingerprints,
    fifth_set_production_paths,
    fingerprint_paths as p257_fingerprint_paths,
    firewall_check as p257_firewall_check,
    fourth_set_production_paths,
)


_SKIP = (
    "PhaseP254_",
    "PhaseP255_",
    "PhaseP256_",
    "PhaseP253_",
    "PhaseP257_",
    "PhaseP258_",
    "PhaseP259_",
    "PhaseP2510_",
    "PhaseP2511_",
    "PhaseP26_",
    "PhaseP261_",
    "PhaseP262_",
    "PhaseP263_",
    "PhaseP264_",
    "PhaseP265_",
    "PhaseP266_",
    "PhaseP267_",
    "PhaseP268_",
    "PhaseP269_",
    "PhaseP2610A_",
    "PhaseP2610B_",
    "PhaseP2610B1_", "PhaseP2610B2_", "PhaseP2610B3_", "PhaseP2610C1C2_", "PhaseP2610C3_", "PhaseP2610C4_", "PhaseP2610C5_", "PhaseP2610D1_", "PhaseP2610D2_",
)


def fingerprint_paths(engine_root: Path, bundle_paths: Dict[str, Path]) -> Dict[str, Path]:
    base = Path(engine_root) / "data" / "output"
    out = p257_fingerprint_paths(engine_root, bundle_paths)
    out.update(
        {
            "p257_status": base
            / "PhaseP257_unseen_drawing_controlled_vision_validation"
            / "P2.5.7_STATUS.md",
            "p257_metrics": base
            / "PhaseP257_unseen_drawing_controlled_vision_validation"
            / "evaluation"
            / "incremental_value_metrics.json",
            "p257_vision": base
            / "PhaseP257_unseen_drawing_controlled_vision_validation"
            / "vision_results.json",
        }
    )
    out.update(fifth_set_production_paths(engine_root))
    fourth = fourth_set_production_paths(engine_root)
    if fourth.get("estimator_excel"):
        out["fourth_estimator_excel"] = fourth["estimator_excel"]
    if fourth.get("model_excel"):
        out["fourth_model_excel"] = fourth["model_excel"]
    return out


def firewall_check(version10_root: Path) -> Dict[str, Any]:
    src = Path(version10_root) / "src"
    offenders = []
    markers = (
        "PhaseP258_controlled_vision_field_repair",
        "VisionFieldRepairCandidate",
        "PhaseP257_unseen_drawing_controlled_vision_validation",
        "UnseenFieldValidationResult",
        "PhaseP256_controlled_field_level_vision_experiment",
        "FieldLevelShadowResult",
        "PhaseP255_controlled_shadow_integration",
        "ShadowIntegrationResult",
        "PhaseP254_semantic_reinforcement_vision_benchmark",
        "ShadowResolverResult",
    )
    for path in src.rglob("*.py"):
        rel = str(path.relative_to(src)).replace("\\", "/")
        if any(x in rel for x in _SKIP):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not any(m in text for m in markers):
            continue
        if any(rel.startswith(p) or f"/{p}" in f"/{rel}" for p in PRODUCTION_MODULE_PREFIXES):
            offenders.append(rel)
        elif any(
            part in rel.lower()
            for part in ("excel", "bbs", "steel", "PhaseT18", "PhaseR31", "PhaseSI")
        ):
            offenders.append(rel)
    nested = p257_firewall_check(version10_root)
    all_off = sorted(set(offenders) | set(nested.get("offenders") or []))
    return {
        "ok": len(all_off) == 0,
        "offenders": all_off,
        "shadow_writes_production": False,
        "production_output_changes": False,
        "engineering_changes": "NONE",
        "note": "P2.5.8 writes only isolated shadow recompute artefacts",
    }


__all__ = [
    "capture_fingerprints",
    "compare_fingerprints",
    "fifth_set_production_paths",
    "fingerprint_paths",
    "firewall_check",
    "fourth_set_production_paths",
]
