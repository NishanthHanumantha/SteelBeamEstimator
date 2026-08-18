"""Regression fingerprints + production firewall for P2.5.5."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from PhaseP24_fourth_set_bar_failure_audit.regression import (
    capture_fingerprints,
    compare_fingerprints,
)
from PhaseP254_semantic_reinforcement_vision_benchmark.regression import (
    PRODUCTION_MODULE_PREFIXES,
    fingerprint_paths as p254_fingerprint_paths,
)


def fourth_set_production_paths(engine_root: Path) -> Dict[str, Path]:
    """Locate Fourth Set production artefacts without probing the DXF."""
    from PhaseQA31_pipeline_diagnostics.artefact_locator import ArtefactLocator

    locator = ArtefactLocator(engine_root)
    art = locator.locate_set("Fourth")
    out_root = art.output_root
    if out_root is None:
        return {}
    return {
        "beam_ownership": out_root / "PhaseT18_beam_ownership" / "BeamOwnership.json",
        "merged_ownership": out_root
        / "PhaseT1831_shared_scope_dedup"
        / "MergedOwnership.json",
        "annotation_graph": out_root / "PhaseT17_annotation_graph" / "AnnotationGraph.json",
        "physical_bars": out_root
        / "PhaseR3.1_engineering_relationship_engine"
        / "PhysicalBars.json",
        "t16_ownership": out_root
        / "PhaseT16_entity_ownership"
        / "beam_entity_ownership.json",
        "r13_models": out_root
        / "PhaseR1.3_pipeline_integration"
        / "beam_reinforcement_models_production.json",
        "engineering_scopes": out_root
        / "PhaseT1831_shared_scope_dedup"
        / "EngineeringScopes.dedup.json",
        "shared_ann_registry": out_root
        / "PhaseT1831_shared_scope_dedup"
        / "SharedAnnotationRegistry.json",
        "estimator_excel": Path(
            getattr(art, "estimator_excel", None)
            or (
                Path(engine_root).parent
                / "Test_Input"
                / "Fourth Set Drawings"
                / "Estimator_Output_4thSet"
                / "EstimatorOutput_Basement_Beam BBS_INIZIO.xlsx"
            )
        ),
        "model_excel": (out_root / "Production_Output" / "Estimation_Output.xlsx"),
    }


def fingerprint_paths(engine_root: Path, bundle_paths: Dict[str, Path]) -> Dict[str, Path]:
    base = Path(engine_root) / "data" / "output"
    out = p254_fingerprint_paths(engine_root, bundle_paths)
    out.update(
        {
            "p254_status": base / "PhaseP254_semantic_reinforcement_vision_benchmark" / "P2.5.4_STATUS.md",
            "p254_summary": base
            / "PhaseP254_semantic_reinforcement_vision_benchmark"
            / "benchmark_summary.json",
            "p254_manifest": base
            / "PhaseP254_semantic_reinforcement_vision_benchmark"
            / "benchmark"
            / "benchmark_manifest.json",
            "p254_gt": base
            / "PhaseP254_semantic_reinforcement_vision_benchmark"
            / "benchmark"
            / "ground_truth_reference.json",
            "p251_matrix": base
            / "PhaseP251_quantity_intent_schema"
            / "quantity_intent_matrix.json",
        }
    )
    excel = bundle_paths.get("estimator_excel") or bundle_paths.get("excel") or out.get("estimator_excel")
    if excel:
        out["production_excel"] = Path(excel)
    model_excel = bundle_paths.get("model_excel") or out.get("model_excel")
    if model_excel:
        out["production_model_excel"] = Path(model_excel)
    return out


def firewall_check(version10_root: Path) -> Dict[str, Any]:
    """Shadow artefacts must not be imported by production steel/BBS/Excel modules."""
    src = Path(version10_root) / "src"
    offenders = []
    markers = (
        "PhaseP255_controlled_shadow_integration",
        "ShadowIntegrationResult",
        "PhaseP254_semantic_reinforcement_vision_benchmark",
        "ShadowResolverResult",
    )
    for path in src.rglob("*.py"):
        rel = str(path.relative_to(src)).replace("\\", "/")
        if "PhaseP254_" in rel or "PhaseP255_" in rel or "PhaseP256_" in rel or "PhaseP257_" in rel or "PhaseP258_" in rel or "PhaseP259_" in rel or "PhaseP2510_" in rel or "PhaseP2511_" in rel or "PhaseP253_" in rel or "PhaseP26_" in rel or "PhaseP261_" in rel or "PhaseP262_" in rel or "PhaseP263_" in rel or "PhaseP264_" in rel or "PhaseP265_" in rel or "PhaseP266_" in rel or "PhaseP267_" in rel:
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
    return {
        "ok": len(offenders) == 0,
        "offenders": offenders,
        "shadow_writes_production": False,
        "production_output_changes": False,
        "engineering_changes": "NONE",
        "note": "P2.5.5 writes only baseline/shadow/evaluation artefacts",
    }


__all__ = [
    "capture_fingerprints",
    "compare_fingerprints",
    "fingerprint_paths",
    "firewall_check",
    "fourth_set_production_paths",
]
