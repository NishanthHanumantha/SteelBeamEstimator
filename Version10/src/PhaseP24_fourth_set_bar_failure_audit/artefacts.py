"""
Load Fourth Set production artefacts (read-only).
MODEL_VERSION: 10.6.0
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from PhaseQA31_pipeline_diagnostics.artefact_locator import ArtefactLocator


def _load(path: Optional[Path]) -> Any:
    if not path or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass
class FourthSetBundle:
    drawing_set: str
    set_key: str
    run_root: Path
    output_root: Path
    estimator_excel: Path
    model_excel: Path
    reinforcement_dxf: Optional[Path]
    beam_ownership: Dict[str, Any]
    merged_ownership: Dict[str, Any]
    annotation_graph: Dict[str, Any]
    physical_bars_r31: Dict[str, Any]
    t16_ownership: Dict[str, Any]
    r13_models: Dict[str, Any]
    engineering_scopes: Dict[str, Any]
    shared_annotation_registry: Dict[str, Any]
    geometry_envelopes: Optional[Dict[str, Any]]
    paths: Dict[str, Path] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    # indexes
    graph_nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    bars_by_beam: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    r31_by_beam: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    t16_by_beam: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    r13_by_beam: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    anns_by_beam: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    leaders_by_beam: Dict[str, List[str]] = field(default_factory=dict)
    dxf_handles: Set[str] = field(default_factory=set)
    dxf_beam_index: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    envelope_beams: Set[str] = field(default_factory=set)


def load_fourth_set_bundle(engine_root: Path) -> FourthSetBundle:
    locator = ArtefactLocator(engine_root)
    art = locator.locate_set("Fourth")
    out = art.output_root
    if out is None or not out.exists():
        raise FileNotFoundError("Fourth Set web_run output_root not found")

    qa30 = engine_root / "data" / "output" / "PhaseQA30_unseen_benchmark"
    prod = _load(qa30 / "ProductionResult.json") or {}
    est_excel = None
    mod_excel = None
    for item in prod.get("sets") or []:
        if item.get("set_key") == "Fourth" or "Fourth" in str(item.get("drawing_set")):
            est_excel = Path(item["estimator_excel"])
            mod_excel = Path(item["model_excel"])
            break
    if est_excel is None:
        est_excel = (
            engine_root.parent
            / "Test_Input"
            / "Fourth Set Drawings"
            / "Estimator_Output_4thSet"
            / "EstimatorOutput_Basement_Beam BBS_INIZIO.xlsx"
        )
    if mod_excel is None:
        mod_excel = out / "Production_Output" / "Estimation_Output.xlsx"

    paths = {
        "beam_ownership": out / "PhaseT18_beam_ownership" / "BeamOwnership.json",
        "merged_ownership": out
        / "PhaseT1831_shared_scope_dedup"
        / "MergedOwnership.json",
        "annotation_graph": out / "PhaseT17_annotation_graph" / "AnnotationGraph.json",
        "physical_bars": out
        / "PhaseR3.1_engineering_relationship_engine"
        / "PhysicalBars.json",
        "t16_ownership": out
        / "PhaseT16_entity_ownership"
        / "beam_entity_ownership.json",
        "r13_models": out
        / "PhaseR1.3_pipeline_integration"
        / "beam_reinforcement_models_production.json",
        "engineering_scopes": out
        / "PhaseT1831_shared_scope_dedup"
        / "EngineeringScopes.dedup.json",
        "shared_ann_registry": out
        / "PhaseT1831_shared_scope_dedup"
        / "SharedAnnotationRegistry.json",
        "geometry_envelopes": out
        / "PhaseT1_geometric_stirrup_evidence"
        / "geometry_envelopes.json",
        "t18": out / "PhaseT18_beam_ownership" / "BeamOwnership.json",
        "p22_regression": engine_root
        / "data"
        / "output"
        / "PhaseP22_leader_chain_evidence"
        / "P22_regression.json",
        "p23_regression": engine_root
        / "data"
        / "output"
        / "PhaseP23_controlled_production_gate"
        / "RegressionReport.json",
        "p231_regression": engine_root
        / "data"
        / "output"
        / "PhaseP23_1_controlled_engineering_recompute"
        / "RegressionReport.json",
    }

    bundle = FourthSetBundle(
        drawing_set=art.drawing_set,
        set_key="Fourth",
        run_root=art.run_root or out.parent.parent,
        output_root=out,
        estimator_excel=est_excel,
        model_excel=mod_excel,
        reinforcement_dxf=art.reinforcement_dxf,
        beam_ownership=_load(paths["beam_ownership"]) or {},
        merged_ownership=_load(paths["merged_ownership"]) or {},
        annotation_graph=_load(paths["annotation_graph"]) or {},
        physical_bars_r31=_load(paths["physical_bars"]) or {},
        t16_ownership=_load(paths["t16_ownership"]) or {},
        r13_models=_load(paths["r13_models"]) or {},
        engineering_scopes=_load(paths["engineering_scopes"]) or {},
        shared_annotation_registry=_load(paths["shared_ann_registry"]) or {},
        geometry_envelopes=_load(paths["geometry_envelopes"]),
        paths=paths,
        warnings=list(art.warnings),
    )
    _build_indexes(bundle)
    from .dxf_probe import build_dxf_beam_index

    print("[P2.4] probing reinforcement DXF for Stage-1 geometry index...")
    bundle.dxf_beam_index = build_dxf_beam_index(bundle.reinforcement_dxf)
    print(f"[P2.4] dxf_beam_marks_indexed={len(bundle.dxf_beam_index)}")
    return bundle


def _build_indexes(bundle: FourthSetBundle) -> None:
    nodes = bundle.annotation_graph.get("nodes") or []
    for n in nodes:
        nid = n.get("id")
        if nid:
            bundle.graph_nodes[nid] = n
        if n.get("type") == "PhysicalBar":
            bid = n.get("beam_id") or (n.get("attributes") or {}).get("beam_id")
            if bid:
                bundle.bars_by_beam.setdefault(bid, []).append(n)
            h = (n.get("attributes") or {}).get("dxf_handle")
            if h:
                bundle.dxf_handles.add(str(h).upper())

    for b in bundle.physical_bars_r31.get("bars") or []:
        bid = b.get("beam_id")
        if bid:
            bundle.r31_by_beam.setdefault(bid, []).append(b)

    t16 = bundle.t16_ownership.get("by_beam") or {}
    for bid, ents in t16.items():
        if isinstance(ents, list):
            bundle.t16_by_beam[bid] = ents
            for e in ents:
                h = e.get("handle")
                if h:
                    bundle.dxf_handles.add(str(h).upper())

    for m in bundle.r13_models.get("models") or []:
        bid = m.get("beam_id")
        if bid:
            bundle.r13_by_beam[bid] = m

    own = bundle.beam_ownership.get("by_beam") or {}
    for bid, rec in own.items():
        bundle.anns_by_beam[bid] = list(rec.get("accepted_annotations") or [])
        bundle.leaders_by_beam[bid] = list(rec.get("leader_results") or [])

    ge = bundle.geometry_envelopes or {}
    by = ge.get("by_beam") or {}
    if isinstance(by, dict):
        bundle.envelope_beams = set(by.keys())
