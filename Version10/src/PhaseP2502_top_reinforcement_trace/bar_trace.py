"""End-to-end bar traces: DXF → R.3.1 → T18 → evidence."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import BAR_DXF_HANDLE_HINTS
from .dxf_trace import entity_record, find_entity_by_handle, find_line_by_coords
from .spatial_metrics import bar_spatial_vs_beam, euclid


def _r31_by_id(r31: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(b.get("bar_id")): b
        for b in (r31.get("bars") or [])
        if b.get("bar_id")
    }


def trace_bar(
    *,
    bar_id: str,
    beam_id: str,
    msp: Any,
    r31: Dict[str, Any],
    ownership: Dict[str, Any],
    graph_node: Optional[Dict[str, Any]],
    ann_pos: Optional[Dict[str, float]],
    leader_geom: Optional[Dict[str, float]],
    neighbour_beams: List[str],
) -> Dict[str, Any]:
    r31b = _r31_by_id(r31).get(bar_id) or {}
    br = (ownership.get("bar_results") or {}).get(bar_id) or {}
    env = ownership.get("envelope") or {}
    concrete = env.get("concrete_envelope") or {}
    depth = float(env.get("depth_mm") or 600.0)

    # Locate DXF entity
    hint = BAR_DXF_HANDLE_HINTS.get(bar_id)
    ent = find_entity_by_handle(msp, hint) if hint else None
    if ent is None and r31b:
        ent = find_line_by_coords(
            msp,
            y=float(r31b["y_position"]),
            start_x=float(r31b["start_x"]),
            end_x=float(r31b["end_x"]),
            layer=r31b.get("layer"),
        )
    dxf = entity_record(ent)

    bar_y = float(r31b.get("y_position") or dxf.get("y_position") or 0.0)
    bar_sx = float(r31b.get("start_x") or 0.0)
    bar_ex = float(r31b.get("end_x") or 0.0)
    spatial = {}
    if concrete:
        spatial = bar_spatial_vs_beam(
            bar_y=bar_y,
            bar_sx=bar_sx,
            bar_ex=bar_ex,
            concrete=concrete,
            depth_mm=depth,
        )

    ann_dist = None
    if ann_pos and ann_pos.get("x") is not None:
        ann_dist = euclid(
            float(ann_pos["x"]),
            float(ann_pos["y"]),
            (bar_sx + bar_ex) / 2.0,
            bar_y,
        )
    tip_dist = None
    if leader_geom and leader_geom.get("tip_x") is not None:
        tip_dist = euclid(
            float(leader_geom["tip_x"]),
            float(leader_geom["tip_y"]),
            (bar_sx + bar_ex) / 2.0,
            bar_y,
        )

    return {
        "bar_id": bar_id,
        "beam_id": beam_id,
        "1_dxf_entity_id": dxf.get("handle"),
        "2_dxf_entity_type": dxf.get("dxftype"),
        "3_layer": dxf.get("layer") or r31b.get("layer"),
        "4_raw_dxf_coordinates": dxf.get("raw_coords"),
        "5_block_insert_transform": dxf.get("block_transform"),
        "6_rotation": dxf.get("rotation"),
        "7_scaling": dxf.get("scaling"),
        "8_translation": dxf.get("translation"),
        "9_final_r31_coordinates": {
            "start_x": r31b.get("start_x"),
            "end_x": r31b.get("end_x"),
            "y_position": r31b.get("y_position"),
        },
        "10_r31_semantic": "PhysicalBar / horizontal LINE on rein layer",
        "11_r31_role_vertical_placement": r31b.get("vertical_placement"),
        "12_r31_source": "PhaseR3.1 PhysicalBarDetector (UUID bar_id, not DXF handle)",
        "13_t18_candidate": True,
        "14_t18_accepted": br.get("accepted"),
        "15_t18_rejection_rule": br.get("rejected_rule"),
        "16_t18_rejection_reason": br.get("ownership_reason"),
        "17_relationship_to_target_beam": {
            "graph_beam_id": (graph_node or {}).get("beam_id"),
            "r31_beam_id": r31b.get("beam_id"),
            "spatial": spatial,
        },
        "18_neighbour_beams": neighbour_beams,
        "19_distance_from_beam_geometry_mm": spatial.get("beam_to_bar_euclidean_mm"),
        "20_corresponds_to_4Y25_visually": False,  # filled by classifier with evidence
        "metrics": {
            **spatial,
            "annotation_to_bar_distance_mm": round(ann_dist, 3) if ann_dist is not None else None,
            "leader_tip_to_bar_distance_mm": round(tip_dist, 3) if tip_dist is not None else None,
            "r31_detection_status": "DETECTED" if r31b else "MISSING",
            "t18_acceptance_status": "ACCEPTED" if br.get("accepted") else "REJECTED",
            "t18_rejection_rule": br.get("rejected_rule"),
        },
        "dxf_probe": dxf,
        "note": (
            "R.3.1 bar_id is a generated UUID token (BAR::{hex8}), not the DXF handle. "
            f"Matched DXF handle via coordinates/hint={hint}."
        ),
    }


def trace_own_entity(
    *,
    own_id: str,
    handle: str,
    beam_id: str,
    msp: Any,
    graph_node: Optional[Dict[str, Any]],
    ownership: Dict[str, Any],
    ann_pos: Optional[Dict[str, float]],
    leader_geom: Optional[Dict[str, float]],
) -> Dict[str, Any]:
    ent = find_entity_by_handle(msp, handle)
    dxf = entity_record(ent)
    env = ownership.get("envelope") or {}
    concrete = env.get("concrete_envelope") or {}
    depth = float(env.get("depth_mm") or 600.0)
    attrs = (graph_node or {}).get("attributes") or {}
    y = dxf.get("y_position")
    bbox = dxf.get("bbox") or []
    sx = bbox[0] if len(bbox) >= 4 else None
    ex = bbox[2] if len(bbox) >= 4 else None
    spatial = {}
    if concrete and y is not None and sx is not None and ex is not None:
        spatial = bar_spatial_vs_beam(
            bar_y=float(y),
            bar_sx=float(sx),
            bar_ex=float(ex),
            concrete=concrete,
            depth_mm=depth,
        )
    tip_dist = None
    if leader_geom and y is not None and sx is not None and ex is not None:
        tip_dist = euclid(
            float(leader_geom["tip_x"]),
            float(leader_geom["tip_y"]),
            (float(sx) + float(ex)) / 2.0,
            float(y),
        )
    ann_dist = None
    if ann_pos and y is not None and sx is not None:
        ann_dist = euclid(
            float(ann_pos["x"]),
            float(ann_pos["y"]),
            (float(sx) + float(ex)) / 2.0,
            float(y),
        )
    return {
        "own_id": own_id,
        "beam_id": beam_id,
        "dxf": dxf,
        "graph_attributes": attrs,
        "role": attrs.get("role"),
        "ownership": attrs.get("ownership"),
        "layer": attrs.get("layer") or dxf.get("layer"),
        "spatial_vs_beam": spatial,
        "annotation_to_geometry_mm": round(ann_dist, 3) if ann_dist is not None else None,
        "leader_tip_to_geometry_mm": round(tip_dist, 3) if tip_dist is not None else None,
        "inside_top_bar_band": "inside_top_bar_band"
        in str(attrs.get("reasons") or []),
        "is_actual_top_reinforcement_geometry": bool(
            spatial.get("bar_vs_envelope_position") == "inside"
            and attrs.get("role") == "TOP_BAR"
        ),
    }
