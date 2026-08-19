"""Regression fingerprints + production firewall for P2.5.9."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from PhaseP254_semantic_reinforcement_vision_benchmark.regression import (
    PRODUCTION_MODULE_PREFIXES,
)
from PhaseP258_controlled_vision_field_repair.regression import (
    capture_fingerprints,
    compare_fingerprints,
    fifth_set_production_paths,
    fingerprint_paths as p258_fingerprint_paths,
    firewall_check as p258_firewall_check,
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
)


def fingerprint_paths(engine_root: Path, bundle_paths: Dict[str, Path]) -> Dict[str, Path]:
    base = Path(engine_root) / "data" / "output"
    out = p258_fingerprint_paths(engine_root, bundle_paths)
    out.update(
        {
            "p258_status": base
            / "PhaseP258_controlled_vision_field_repair"
            / "P2.5.8_STATUS.md",
            "p258_promoted": base
            / "PhaseP258_controlled_vision_field_repair"
            / "promoted_repairs.json",
            "p257_vision": base
            / "PhaseP257_unseen_drawing_controlled_vision_validation"
            / "vision_results.json",
        }
    )
    out.update(fifth_set_production_paths(engine_root))
    return out


def firewall_check(version10_root: Path) -> Dict[str, Any]:
    src = Path(version10_root) / "src"
    offenders = []
    markers = (
        "PhaseP259_beam_safe_arbitration",
        "PhaseP258_controlled_vision_field_repair",
        "VisionFieldRepairCandidate",
        "PhaseP257_unseen_drawing_controlled_vision_validation",
        "PhaseP256_controlled_field_level_vision_experiment",
        "PhaseP255_controlled_shadow_integration",
        "PhaseP254_semantic_reinforcement_vision_benchmark",
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
    nested = p258_firewall_check(version10_root)
    all_off = sorted(set(offenders) | set(nested.get("offenders") or []))
    return {
        "ok": len(all_off) == 0,
        "offenders": all_off,
        "shadow_writes_production": False,
        "production_output_changes": False,
        "engineering_changes": "NONE",
        "note": "P2.5.9 writes only isolated strategy-comparison artefacts",
    }


__all__ = [
    "capture_fingerprints",
    "compare_fingerprints",
    "fingerprint_paths",
    "firewall_check",
]
