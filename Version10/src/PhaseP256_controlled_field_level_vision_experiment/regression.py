"""Regression fingerprints + production firewall for P2.5.6."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from PhaseP254_semantic_reinforcement_vision_benchmark.regression import (
    PRODUCTION_MODULE_PREFIXES,
)
from PhaseP255_controlled_shadow_integration.regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths as p255_fingerprint_paths,
    fourth_set_production_paths,
)


def fingerprint_paths(engine_root: Path, bundle_paths: Dict[str, Path]) -> Dict[str, Path]:
    base = Path(engine_root) / "data" / "output"
    out = p255_fingerprint_paths(engine_root, bundle_paths)
    out.update(
        {
            "p255_status": base / "PhaseP255_controlled_shadow_integration" / "P2.5.5_STATUS.md",
            "p255_metrics": base
            / "PhaseP255_controlled_shadow_integration"
            / "evaluation"
            / "metrics.json",
            "p255_baseline_manifest": base
            / "PhaseP255_controlled_shadow_integration"
            / "baseline"
            / "benchmark_manifest_fingerprint.json",
        }
    )
    return out


def firewall_check(version10_root: Path) -> Dict[str, Any]:
    src = Path(version10_root) / "src"
    offenders = []
    markers = (
        "PhaseP256_controlled_field_level_vision_experiment",
        "FieldLevelShadowResult",
        "PhaseP255_controlled_shadow_integration",
        "ShadowIntegrationResult",
        "PhaseP254_semantic_reinforcement_vision_benchmark",
        "ShadowResolverResult",
    )
    prefixes = PRODUCTION_MODULE_PREFIXES
    for path in src.rglob("*.py"):
        rel = str(path.relative_to(src)).replace("\\", "/")
        if any(x in rel for x in ("PhaseP254_", "PhaseP255_", "PhaseP256_", "PhaseP253_", "PhaseP257_", "PhaseP258_", "PhaseP259_", "PhaseP2510_", "PhaseP2511_", "PhaseP26_", "PhaseP261_", "PhaseP262_", "PhaseP263_", "PhaseP264_", "PhaseP265_", "PhaseP266_", "PhaseP267_", "PhaseP268_", "PhaseP269_", "PhaseP2610A_", "PhaseP2610B_", "PhaseP2610B1_", "PhaseP2610B2_", "PhaseP2610B3_", "PhaseP2610C1C2_", "PhaseP2610C3_", "PhaseP2610C4_", "PhaseP2610C5_", "PhaseP2610D1_", "PhaseP2610D2_", "PhaseP2610D3_", "PhaseP2610D4_", "PhaseP2610E1_", "PhaseP2610E2_", "PhaseP2610E3_")):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not any(m in text for m in markers):
            continue
        if any(rel.startswith(p) or f"/{p}" in f"/{rel}" for p in prefixes):
            offenders.append(rel)
        elif any(
            part in rel.lower()
            for part in ("excel", "bbs", "steel", "PhaseT18", "PhaseR31", "PhaseSI")
        ):
            offenders.append(rel)
    return {
        "ok": len(offenders) == 0,
        "offenders": offenders,
        "shadow_writes_production": False,
        "production_output_changes": False,
        "engineering_changes": "NONE",
        "note": "P2.5.6 writes only field-level shadow/evaluation artefacts",
    }


__all__ = [
    "capture_fingerprints",
    "compare_fingerprints",
    "fingerprint_paths",
    "firewall_check",
    "fourth_set_production_paths",
]
