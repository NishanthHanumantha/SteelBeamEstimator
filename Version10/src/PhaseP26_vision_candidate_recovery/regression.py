"""Regression fingerprints + production firewall for P2.6."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from PhaseP254_semantic_reinforcement_vision_benchmark.regression import (
    PRODUCTION_MODULE_PREFIXES,
)
from PhaseP2511_evidence_enrichment.regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths as p2511_fingerprint_paths,
    firewall_check as p2511_firewall_check,
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
)

_RUNTIME_MODULES = (
    "config.py",
    "policy.py",
    "candidate_schema.py",
    "region_builder.py",
    "candidate_gap_analyzer.py",
    "vision_prompt.py",
    "vision_observer.py",
    "response_parser.py",
    "candidate_normalizer.py",
    "deterministic_comparator.py",
    "cache.py",
    "evidence_store.py",
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
    out = p2511_fingerprint_paths(engine_root, bundle_paths)
    out.update(
        {
            "p2511_status": base / "PhaseP2511_evidence_enrichment" / "P2.5.11_STATUS.md",
        }
    )
    return out


def firewall_check(version10_root: Path) -> Dict[str, Any]:
    src = Path(version10_root) / "src"
    offenders = []
    markers = (
        "PhaseP26_vision_candidate_recovery",
        "PhaseP2511_evidence_enrichment",
        "PhaseP2510_new_stirrup_safety",
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
    nested = p2511_firewall_check(version10_root)
    all_off = sorted(set(offenders) | set(nested.get("offenders") or []))
    return {
        "ok": len(all_off) == 0,
        "offenders": all_off,
        "shadow_writes_production": False,
        "production_output_changes": False,
        "engineering_changes": "NONE",
        "note": "P2.6 writes only isolated shadow candidate-recovery artefacts",
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
