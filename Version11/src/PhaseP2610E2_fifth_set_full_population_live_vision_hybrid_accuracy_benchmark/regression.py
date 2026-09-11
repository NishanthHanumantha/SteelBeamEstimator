"""Regression fingerprints + production firewall for P2.6.10-E.2."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from PhaseP254_semantic_reinforcement_vision_benchmark.regression import (
    PRODUCTION_MODULE_PREFIXES,
)
from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths as p2610e1_fingerprint_paths,
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
    "PhaseP2610C1C2_",
    "PhaseP2610C3_",
    "PhaseP2610C4_",
    "PhaseP2610C5_",
    "PhaseP2610D1_",
    "PhaseP2610D2_",
    "PhaseP2610D3_",
    "PhaseP2610D4_",
    "PhaseP2610E1_",
    "PhaseP2610E2_", "PhaseP2610E3_",
)

_RUNTIME_MODULES = (
    "population.py",
    "visual_sources.py",
    "eligibility.py",
    "artefact_reuse.py",
    "checkpoint.py",
    "vision_loop.py",
    "subset_kpis.py",
)
_LIVE_MODULE = "live_caller.py"


def fingerprint_paths(engine_root: Path, bundle_paths: Dict[str, Path]) -> Dict[str, Path]:
    base = Path(engine_root) / "data" / "output"
    out = p2610e1_fingerprint_paths(engine_root, bundle_paths)
    out.update(
        {
            "p2610e1_results": base / "PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark" / "P2.6.10-E.1_RESULTS.json",
            "p2610c5_results": base / "PhaseP2610C5_stratified_vision_semantic_benchmark" / "P2.6.10-C.5_RESULTS.json",
            "p2610c4_results": base / "PhaseP2610C4_shadow_truth_reconciliation_benchmark_calibration" / "P2.6.10-C.4_RESULTS.json",
            "p2610c3_results": base / "PhaseP2610C3_visual_completeness_claude_shadow" / "P2.6.10-C.3_RESULTS.json",
            "p2610d4_results": base / "PhaseP2610D4_shadow_hybrid_engineering_calculation_accuracy_benchmark" / "P2.6.10-D.4_RESULTS.json",
            "p2610d3_results": base / "PhaseP2610D3_hybrid_engineering_binding_compatibility" / "P2.6.10-D.3_RESULTS.json",
            "p2610d2_results": base / "PhaseP2610D2_shadow_hybrid_semantic_resolver" / "P2.6.10-D.2_RESULTS.json",
            "p2610d1_results": base / "PhaseP2610D1_vision_semantic_contract_hybrid_foundation" / "P2.6.10-D.1_RESULTS.json",
            "p2610d1_contract": base / "PhaseP2610D1_vision_semantic_contract_hybrid_foundation" / "hybrid_authority_contract.json",
        }
    )
    for key in ("r13_models", "steel_weight_summary", "bbs_summary", "estimator_workbook"):
        if bundle_paths.get(key):
            out[key] = Path(bundle_paths[key])
    return out


def firewall_check(version10_root: Path) -> Dict[str, Any]:
    src = Path(version10_root) / "src"
    offenders = []
    markers = (
        "PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark",
        "PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark",
    )
    for path in src.iterdir():
        if not path.is_dir():
            continue
        rel_top = path.name
        if any(x in rel_top for x in _SKIP):
            continue
        for py in path.rglob("*.py"):
            rel = str(py.relative_to(src)).replace("\\", "/")
            if any(x in rel for x in _SKIP):
                continue
            try:
                text = py.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if not any(m in text for m in markers):
                continue
            if any(rel.startswith(p) or f"/{p}" in f"/{rel}" for p in PRODUCTION_MODULE_PREFIXES):
                offenders.append(rel)
            elif any(part in rel.lower() for part in ("excel", "bbs", "steel", "PhaseR31", "PhaseSI")):
                offenders.append(rel)
    return {
        "ok": len(offenders) == 0,
        "offenders": sorted(set(offenders)),
        "shadow_writes_production": False,
        "note": "P2.6.10-E.2 writes only isolated live-benchmark artefacts",
    }


def runtime_leakage_scan(package_dir: Path) -> Dict[str, Any]:
    hits: List[Dict[str, str]] = []
    extra = ("ezdxf", "RenderSession", "LIVE_SHADOW")
    for name in list(_RUNTIME_MODULES) + [_LIVE_MODULE]:
        path = Path(package_dir) / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for tok in FORBIDDEN_GATE_TOKENS:
            if tok in text:
                hits.append({"file": name, "token": tok})
        for tok in extra:
            if tok in text:
                hits.append({"file": name, "token": tok})
        if name != _LIVE_MODULE:
            for tok in ("call_claude", "call_selected_beam", "generate_vision_response"):
                if tok in text:
                    hits.append({"file": name, "token": tok})
    return {"ok": len(hits) == 0, "hits": hits}


def prior_artefacts_intact(version10_root: Path) -> Dict[str, Any]:
    root = Path(version10_root) / "data" / "output"
    needed = [
        root / "PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark" / "P2.6.10-E.1_RESULTS.json",
        root / "PhaseP2610D4_shadow_hybrid_engineering_calculation_accuracy_benchmark" / "P2.6.10-D.4_RESULTS.json",
        root / "PhaseP2610D3_hybrid_engineering_binding_compatibility" / "P2.6.10-D.3_RESULTS.json",
        root / "PhaseP2610D2_shadow_hybrid_semantic_resolver" / "P2.6.10-D.2_RESULTS.json",
        root / "PhaseP2610D1_vision_semantic_contract_hybrid_foundation" / "P2.6.10-D.1_RESULTS.json",
        root / "PhaseP2610C5_stratified_vision_semantic_benchmark" / "P2.6.10-C.5_RESULTS.json",
        root / "PhaseP2610C3_visual_completeness_claude_shadow" / "P2.6.10-C.3_RESULTS.json",
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
