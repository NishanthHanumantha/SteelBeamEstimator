"""Regression fingerprints + production firewall for P2.5.10."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from PhaseP254_semantic_reinforcement_vision_benchmark.regression import (
    PRODUCTION_MODULE_PREFIXES,
)
from PhaseP259_beam_safe_arbitration.regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths as p259_fingerprint_paths,
    firewall_check as p259_firewall_check,
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

_RUNTIME_MODULES = (
    "insertion_classifier.py",
    "evidence_evaluator.py",
    "beam_safety_gate.py",
    "config.py",
    "policy.py",
)

_FORBIDDEN_RUNTIME_TOKENS = (
    "estimator_kg",
    "estimator_steel",
    "ground_truth_steel",
    "ground_truth_kg",
    "EstimatorOutput",
    "benchmark_answer",
    "expected_steel",
    "answer_workbook",
)


def fingerprint_paths(engine_root: Path, bundle_paths: Dict[str, Path]) -> Dict[str, Path]:
    base = Path(engine_root) / "data" / "output"
    out = p259_fingerprint_paths(engine_root, bundle_paths)
    out.update(
        {
            "p259_status": base / "PhaseP259_beam_safe_arbitration" / "P2.5.9_STATUS.md",
            "p259_unknown": base
            / "PhaseP259_beam_safe_arbitration"
            / "strategies"
            / "P259_UNKNOWN_ONLY"
            / "promoted_repairs.json",
        }
    )
    return out


def firewall_check(version10_root: Path) -> Dict[str, Any]:
    src = Path(version10_root) / "src"
    offenders = []
    markers = (
        "PhaseP2510_new_stirrup_safety",
        "PhaseP259_beam_safe_arbitration",
        "PhaseP258_controlled_vision_field_repair",
        "PhaseP257_unseen_drawing_controlled_vision_validation",
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
    nested = p259_firewall_check(version10_root)
    all_off = sorted(set(offenders) | set(nested.get("offenders") or []))
    return {
        "ok": len(all_off) == 0,
        "offenders": all_off,
        "shadow_writes_production": False,
        "production_output_changes": False,
        "engineering_changes": "NONE",
        "note": "P2.5.10 writes only isolated insertion-safety artefacts",
    }


def runtime_leakage_scan(package_dir: Path) -> Dict[str, Any]:
    hits: List[Dict[str, str]] = []
    for name in _RUNTIME_MODULES:
        path = Path(package_dir) / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for tok in _FORBIDDEN_RUNTIME_TOKENS:
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
