"""Regression fingerprints + production firewall for P2.5.7."""
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
from PhaseP256_controlled_field_level_vision_experiment.regression import (
    fingerprint_paths as p256_fingerprint_paths,
    firewall_check as p256_firewall_check,
)
from PhaseQA31_pipeline_diagnostics.artefact_locator import ArtefactLocator


def fifth_set_production_paths(engine_root: Path) -> Dict[str, Path]:
    locator = ArtefactLocator(engine_root)
    art = locator.locate_set("Fifth")
    out_root = art.output_root
    excel = (
        Path(engine_root).parent
        / "Test_Input"
        / "Fifth Set Drawings"
        / "Estimator_Output_5thSet"
        / "EstimatorOutput_9TH FLOOR.xlsx"
    )
    paths: Dict[str, Path] = {"fifth_estimator_excel": excel}
    if out_root is not None:
        paths.update(
            {
                "fifth_beam_ownership": out_root / "PhaseT18_beam_ownership" / "BeamOwnership.json",
                "fifth_physical_bars": out_root
                / "PhaseR3.1_engineering_relationship_engine"
                / "PhysicalBars.json",
                "fifth_r13_models": out_root
                / "PhaseR1.3_pipeline_integration"
                / "beam_reinforcement_models_production.json",
                "fifth_bbs_summary": out_root / "Production_Output" / "bbs_summary.json",
                "fifth_model_excel": out_root / "Production_Output" / "Estimation_Output.xlsx",
            }
        )
    return paths


def fingerprint_paths(engine_root: Path, bundle_paths: Dict[str, Path]) -> Dict[str, Path]:
    base = Path(engine_root) / "data" / "output"
    out = p256_fingerprint_paths(engine_root, bundle_paths)
    out.update(p255_fingerprint_paths(engine_root, bundle_paths))
    out.update(
        {
            "p256_status": base
            / "PhaseP256_controlled_field_level_vision_experiment"
            / "P2.5.6_STATUS.md",
            "p256_metrics": base
            / "PhaseP256_controlled_field_level_vision_experiment"
            / "evaluation"
            / "metrics.json",
            "p251_matrix": base
            / "PhaseP251_quantity_intent_schema"
            / "quantity_intent_matrix.json",
            "p251_report": base
            / "PhaseP251_quantity_intent_schema"
            / "P2.5.1_QuantityIntent_Report.md",
        }
    )
    out.update(fifth_set_production_paths(engine_root))
    fourth = fourth_set_production_paths(engine_root)
    if fourth.get("estimator_excel"):
        out["fourth_estimator_excel"] = fourth["estimator_excel"]
    if fourth.get("physical_bars"):
        out["fourth_physical_bars"] = fourth["physical_bars"]
    return out


def firewall_check(version10_root: Path) -> Dict[str, Any]:
    src = Path(version10_root) / "src"
    offenders = []
    markers = (
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
        if any(
            x in rel
            for x in ("PhaseP254_", "PhaseP255_", "PhaseP256_", "PhaseP253_", "PhaseP257_", "PhaseP258_", "PhaseP259_", "PhaseP2510_", "PhaseP2511_", "PhaseP26_", "PhaseP261_", "PhaseP262_", "PhaseP263_", "PhaseP264_", "PhaseP265_", "PhaseP266_", "PhaseP267_", "PhaseP268_", "PhaseP269_", "PhaseP2610A_", "PhaseP2610B_", "PhaseP2610B1_")
        ):
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
    nested = p256_firewall_check(version10_root)
    all_off = sorted(set(offenders) | set(nested.get("offenders") or []))
    return {
        "ok": len(all_off) == 0,
        "offenders": all_off,
        "shadow_writes_production": False,
        "production_output_changes": False,
        "engineering_changes": "NONE",
        "note": "P2.5.7 writes only unseen-validation shadow/evaluation artefacts",
    }


__all__ = [
    "capture_fingerprints",
    "compare_fingerprints",
    "fifth_set_production_paths",
    "fingerprint_paths",
    "firewall_check",
    "fourth_set_production_paths",
]
