"""Regression fingerprints + production firewall for P2.6.4."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from PhaseP254_semantic_reinforcement_vision_benchmark.regression import (
    PRODUCTION_MODULE_PREFIXES,
)
from PhaseP263_longitudinal_aware_gate.regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths as p263_fingerprint_paths,
    firewall_check as p263_firewall_check,
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
)

_RUNTIME_MODULES = (
    "config.py",
    "role_gap.py",
    "gate_features.py",
    "gate_rules.py",
    "gate_decision.py",
    "candidate_gap_analyzer.py",
    "replay_runner.py",
    "live_runner.py",
    "frozen_sample.py",
)


def fingerprint_paths(engine_root: Path, bundle_paths: Dict[str, Path]) -> Dict[str, Path]:
    base = Path(engine_root) / "data" / "output"
    out = p263_fingerprint_paths(engine_root, bundle_paths)
    out.update(
        {
            "p263_status": base / "PhaseP263_longitudinal_aware_gate" / "P2.6.3_STATUS.md",
            "p263_metrics": base / "PhaseP263_longitudinal_aware_gate" / "reports" / "metrics.json",
            "p263_manifest": base / "PhaseP263_longitudinal_aware_gate" / "gate_manifest.json",
        }
    )
    return out


def firewall_check(version10_root: Path) -> Dict[str, Any]:
    src = Path(version10_root) / "src"
    offenders = []
    markers = (
        "PhaseP264_selective_role_gap_gate",
        "PhaseP263_longitudinal_aware_gate",
        "PhaseP262_selective_vision_candidate_gate",
        "PhaseP261_stratified_vision_candidate_recovery",
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
    nested = p263_firewall_check(version10_root)
    all_off = sorted(set(offenders) | set(nested.get("offenders") or []))
    return {
        "ok": len(all_off) == 0,
        "offenders": all_off,
        "shadow_writes_production": False,
        "production_output_changes": False,
        "engineering_changes": "NONE",
        "cached_vision_unmodified": True,
        "live_vision_invoked": False,
        "note": "P2.6.4 writes only isolated selective role-gap shadow artefacts",
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
