"""Regression fingerprints + production firewall for P2.6.10-C.1+C.2."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from PhaseP254_semantic_reinforcement_vision_benchmark.regression import (
    PRODUCTION_MODULE_PREFIXES,
)
from PhaseP2610B3_target_anchor_geometry_context_recovery.regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths as p2610b3_fingerprint_paths,
    firewall_check as p2610b3_firewall_check,
    prior_phase_unit_ok,
)

from .policy import FORBIDDEN_GATE_TOKENS

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
    "PhaseP2610B1_",
    "PhaseP2610B2_",
    "PhaseP2610B3_",
    "PhaseP2610C1C2_", "PhaseP2610C3_", "PhaseP2610C4_", "PhaseP2610C5_", "PhaseP2610D1_", "PhaseP2610D2_", "PhaseP2610D3_", "PhaseP2610D4_", "PhaseP2610E1_", "PhaseP2610E2_", "PhaseP2610E3_",
)

_RUNTIME_MODULES = (
    "inventory.py",
    "selector.py",
)


def fingerprint_paths(engine_root: Path, bundle_paths: Dict[str, Path]) -> Dict[str, Path]:
    base = Path(engine_root) / "data" / "output"
    out = p2610b3_fingerprint_paths(engine_root, bundle_paths)
    out.update(
        {
            "p2610b3_results": base / "PhaseP2610B3_target_anchor_geometry_context_recovery" / "P2.6.10-B.3_RESULTS.json",
            "p2610b3_summary": base / "PhaseP2610B3_target_anchor_geometry_context_recovery" / "validation_summary.json",
            "p2610b2_results": base / "PhaseP2610B2_render_quality_directional_recovery" / "P2.6.10-B.2_RESULTS.json",
            "p2610b1_results": base / "PhaseP2610B1_population_generalization" / "P2.6.10-B.1_RESULTS.json",
        }
    )
    return out


def firewall_check(version10_root: Path) -> Dict[str, Any]:
    src = Path(version10_root) / "src"
    offenders = []
    markers = (
        "PhaseP2610C1C2_evidence_inventory_candidate_selection",
        "PhaseP2610B3_target_anchor_geometry_context_recovery",
        "PhaseP2610B2_render_quality_directional_recovery",
        "PhaseP2610B1_population_generalization",
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
        elif any(part in rel.lower() for part in ("excel", "bbs", "steel", "PhaseR31", "PhaseSI")):
            offenders.append(rel)
    nested = p2610b3_firewall_check(version10_root)
    all_off = sorted(set(offenders) | set(nested.get("offenders") or []))
    return {
        "ok": len(all_off) == 0,
        "offenders": all_off,
        "shadow_writes_production": False,
        "note": "P2.6.10-C.1+C.2 writes only isolated shadow artefacts",
    }


def runtime_leakage_scan(package_dir: Path) -> Dict[str, Any]:
    hits: List[Dict[str, str]] = []
    for name in _RUNTIME_MODULES:
        path = Path(package_dir) / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for tok in FORBIDDEN_GATE_TOKENS:
            if tok in text:
                hits.append({"file": name, "token": tok})
    return {"ok": len(hits) == 0, "hits": hits}


def prior_artefacts_intact(version10_root: Path) -> Dict[str, Any]:
    root = Path(version10_root) / "data" / "output"
    needed = [
        root / "PhaseP2610B_adaptive_beam_detail_crop" / "P2.6.10-B_STATUS.md",
        root / "PhaseP2610B1_population_generalization" / "P2.6.10-B.1_RESULTS.json",
        root / "PhaseP2610B1_population_generalization" / "validation_summary.json",
        root / "PhaseP2610B2_render_quality_directional_recovery" / "P2.6.10-B.2_RESULTS.json",
        root / "PhaseP2610B3_target_anchor_geometry_context_recovery" / "P2.6.10-B.3_RESULTS.json",
        root / "PhaseP2610A_beam_region_crop_audit" / "P2.6.10-A_STATUS.md",
    ]
    missing = [str(p) for p in needed if not p.exists()]
    return {"ok": len(missing) == 0, "missing": missing}


__all__ = [
    "capture_fingerprints",
    "compare_fingerprints",
    "fingerprint_paths",
    "firewall_check",
    "prior_artefacts_intact",
    "prior_phase_unit_ok",
    "runtime_leakage_scan",
]
