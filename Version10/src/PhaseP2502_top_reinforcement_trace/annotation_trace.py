"""Trace 4-Y25 annotation → leader → OWN chain."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .spatial_metrics import euclid


def _graph_by_id(graph: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(n.get("id")): n for n in (graph.get("nodes") or []) if n.get("id")}


def trace_annotation_chain(
    *,
    beam_id: str,
    ann_id: str,
    leader_id: str,
    own_id: str,
    ownership: Dict[str, Any],
    graph: Dict[str, Any],
    evidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    nodes = _graph_by_id(graph)
    ann_n = nodes.get(ann_id) or {}
    ldr_n = nodes.get(leader_id) or {}
    own_n = nodes.get(own_id) or {}
    a_attrs = ann_n.get("attributes") or {}
    l_attrs = ldr_n.get("attributes") or {}

    chains = [
        c
        for c in (ownership.get("accepted_chains") or [])
        if c.get("annotation_id") == ann_id
    ]
    accepted_anns = [
        a
        for a in (ownership.get("accepted_annotations") or [])
        if (a.get("id") or a.get("annotation_id")) == ann_id
    ]

    tip = {
        "x": l_attrs.get("tip_x"),
        "y": l_attrs.get("tip_y"),
    }
    tail = {
        "x": l_attrs.get("tail_x"),
        "y": l_attrs.get("tail_y"),
    }
    ann_pos = {"x": a_attrs.get("x"), "y": a_attrs.get("y")}
    tip_tail = None
    if tip.get("x") is not None and tail.get("x") is not None:
        tip_tail = euclid(float(tip["x"]), float(tip["y"]), float(tail["x"]), float(tail["y"]))
    ann_tail = None
    if ann_pos.get("x") is not None and tail.get("x") is not None:
        ann_tail = euclid(
            float(ann_pos["x"]), float(ann_pos["y"]), float(tail["x"]), float(tail["y"])
        )

    reinf = (evidence or {}).get("reinforcement") or []
    return {
        "beam_id": beam_id,
        "annotation_id": ann_id,
        "raw_text": a_attrs.get("clean_text") or a_attrs.get("text"),
        "annotation_position": ann_pos,
        "leader_id": leader_id,
        "leader_tip": tip,
        "leader_tail": tail,
        "leader_tip_to_tail_mm": round(tip_tail, 3) if tip_tail is not None else None,
        "leader_tail_to_annotation_mm": round(ann_tail, 3) if ann_tail is not None else None,
        "accepted_annotation_record": accepted_anns[0] if accepted_anns else None,
        "accepted_chains": chains,
        "describes": (chains[0].get("describes") if chains else None),
        "own_entity": {
            "id": own_id,
            "attributes": own_n.get("attributes") or {},
            "type": own_n.get("type"),
        },
        "evidence_package_reinforcement_count": len(reinf),
        "why_accepted_chain_with_empty_reinforcement": (
            "Accepted chain describes OWN::* (T16 OwnedEntity TOP_BAR / LWPOLYLINE on "
            "-STR-BEAM), not BAR::* (R.3.1 PhysicalBar). P2.5.0 evidence_pack only "
            "includes AnnotationGraph PhysicalBar nodes from accepted bar_results; "
            "OwnedEntity geometry is not mapped into reinforcement[]."
        ),
        "pipeline": [
            "DXF TEXT/MTEXT",
            "annotation extraction / normalization",
            "leader detection",
            "AnnotationGraph",
            "T18 accepted annotation + accepted_chains",
            f"describes → {own_id}",
            "P2.5.0 evidence package (annotations+leaders only; reinforcement=[])",
        ],
    }
