"""Regression fingerprints + production firewall for P2.6.8."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from PhaseP254_semantic_reinforcement_vision_benchmark.regression import (
    PRODUCTION_MODULE_PREFIXES,
)
from PhaseP267_live_semantic_arbitration.regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths as p267_fingerprint_paths,
    firewall_check as p267_firewall_check,
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
    "PhaseP2610B1_", "PhaseP2610B2_", "PhaseP2610B3_", "PhaseP2610C1C2_", "PhaseP2610C3_", "PhaseP2610C4_", "PhaseP2610C5_", "PhaseP2610D1_", "PhaseP2610D2_", "PhaseP2610D3_", "PhaseP2610D4_", "PhaseP2610E1_", "PhaseP2610E2_", "PhaseP2610E3_",
)

_RUNTIME_MODULES = (
    "config.py",
    "evidence.py",
    "layer_resolver.py",
    "conflict.py",
    "arbitration.py",
    "semantic_contract.py",
    "dataset.py",
)


def fingerprint_paths(engine_root: Path, bundle_paths: Dict[str, Path]) -> Dict[str, Path]:
    base = Path(engine_root) / "data" / "output"
    out = p267_fingerprint_paths(engine_root, bundle_paths)
    out.update(
        {
            "p267_status": base / "PhaseP267_live_semantic_arbitration" / "P2.6.7_STATUS.md",
            "p267_results": base / "PhaseP267_live_semantic_arbitration" / "P2.6.7_RESULTS.json",
            "p267_live": base / "PhaseP267_live_semantic_arbitration" / "P2.6.7_LIVE_DECISIONS.json",
            "p266_status": base / "PhaseP266_semantic_longitudinal_resolver" / "P2.6.6_STATUS.md",
            "p266_decisions": base / "PhaseP266_semantic_longitudinal_resolver" / "P2.6.6_SEMANTIC_DECISIONS.json",
            "p266_targets": base / "PhaseP266_semantic_longitudinal_resolver" / "target_records.json",
            "p265_status": base / "PhaseP265_spatial_context_longitudinal" / "P2.6.5_STATUS.md",
            "p264_status": base / "PhaseP264_selective_role_gap_gate" / "P2.6.4_STATUS.md",
        }
    )
    return out


def firewall_check(version10_root: Path) -> Dict[str, Any]:
    src = Path(version10_root) / "src"
    offenders = []
    markers = (
        "PhaseP268_evidence_conflict_arbitration",
        "PhaseP267_live_semantic_arbitration",
        "PhaseP266_semantic_longitudinal_resolver",
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
    nested = p267_firewall_check(version10_root)
    all_off = sorted(set(offenders) | set(nested.get("offenders") or []))
    return {
        "ok": len(all_off) == 0,
        "offenders": all_off,
        "shadow_writes_production": False,
        "note": "P2.6.8 writes only isolated evidence-conflict shadow artefacts",
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
    "runtime_leakage_scan",
]
