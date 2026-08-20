"""Regression fingerprints + production firewall for P2.6.10-B."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from PhaseP254_semantic_reinforcement_vision_benchmark.regression import (
    PRODUCTION_MODULE_PREFIXES,
)
from PhaseP2610A_beam_region_crop_audit.regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths as p2610a_fingerprint_paths,
    firewall_check as p2610a_firewall_check,
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
    "PhaseP2610B1_", "PhaseP2610B2_", "PhaseP2610B3_", "PhaseP2610C1C2_",
)

_RUNTIME_MODULES = (
    "config.py",
    "evidence.py",
    "envelope.py",
    "completeness.py",
    "evaluator.py",
)


def fingerprint_paths(engine_root: Path, bundle_paths: Dict[str, Path]) -> Dict[str, Path]:
    base = Path(engine_root) / "data" / "output"
    out = p2610a_fingerprint_paths(engine_root, bundle_paths)
    out.update(
        {
            "p2610a_status": base / "PhaseP2610A_beam_region_crop_audit" / "P2.6.10-A_STATUS.md",
            "p2610a_results": base / "PhaseP2610A_beam_region_crop_audit" / "P2.6.10-A_RESULTS.json",
            "p2610a_b55": base / "PhaseP2610A_beam_region_crop_audit" / "P2.6.10-A_B55_DIAGNOSTICS.json",
            "p269_status": base / "PhaseP269_reinforcement_group_interpretation" / "P2.6.9_STATUS.md",
            "p268_status": base / "PhaseP268_evidence_conflict_arbitration" / "P2.6.8_STATUS.md",
            "p267_status": base / "PhaseP267_live_semantic_arbitration" / "P2.6.7_STATUS.md",
            "p266_status": base / "PhaseP266_semantic_longitudinal_resolver" / "P2.6.6_STATUS.md",
        }
    )
    return out


def firewall_check(version10_root: Path) -> Dict[str, Any]:
    src = Path(version10_root) / "src"
    offenders = []
    markers = (
        "PhaseP2610B_adaptive_beam_detail_crop",
        "PhaseP2610A_beam_region_crop_audit",
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
    nested = p2610a_firewall_check(version10_root)
    all_off = sorted(set(offenders) | set(nested.get("offenders") or []))
    return {
        "ok": len(all_off) == 0,
        "offenders": all_off,
        "shadow_writes_production": False,
        "note": "P2.6.10-B writes only isolated adaptive-crop shadow artefacts",
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


__all__ = [
    "capture_fingerprints",
    "compare_fingerprints",
    "fingerprint_paths",
    "firewall_check",
    "prior_phase_unit_ok",
    "runtime_leakage_scan",
]
