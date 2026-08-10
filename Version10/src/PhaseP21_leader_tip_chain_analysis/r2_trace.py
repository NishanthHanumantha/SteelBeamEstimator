"""
Reconstruct existing R2_LEADER_TIP decision path (read-only).
MODEL_VERSION: 10.5.3
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PhaseQA41_dropped_entity_recovery_audit.geometry_helpers import (
    as_bbox,
    dist_point_to_bbox,
)
from PhaseT18_beam_ownership.beam_envelope import tip_in_envelope
from PhaseT18_beam_ownership.ownership_rules import evaluate_leader

from .config import MODEL_VERSION, PHASE_ID


def _null(v: Any) -> Any:
    return v if v is not None else None


def index_graph(graph: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    nodes = {n["id"]: n for n in (graph.get("nodes") or []) if n.get("id")}
    edges = list(graph.get("edges") or [])
    return nodes, edges


def _pointed_bars(edges: List[Dict[str, Any]], leader_id: str) -> List[str]:
    out = []
    for e in edges:
        if e.get("source_id") == leader_id and e.get("type") == "POINTS_TO":
            out.append(str(e.get("target_id")))
    return out


def _associated_annotations(edges: List[Dict[str, Any]], leader_id: str) -> List[str]:
    out = []
    for e in edges:
        if e.get("target_id") == leader_id and e.get("type") == "ATTACHED_TO":
            out.append(str(e.get("source_id")))
    return out


def reconstruct_r2(
    *,
    qa43_row: Dict[str, Any],
    qa41_row: Optional[Dict[str, Any]],
    leader_audit: Optional[Dict[str, Any]],
    beam_own: Dict[str, Any],
    nodes: Dict[str, Dict[str, Any]],
    edges: List[Dict[str, Any]],
    all_envelopes: Dict[str, Dict[str, Any]],
    priority_beams: List[str],
) -> Dict[str, Any]:
    bid = str(qa43_row.get("beam_id") or "")
    eid = str(qa43_row.get("entity_id") or "")
    stable = str(qa43_row.get("stable_key") or f"{bid}::{eid}")
    node = nodes.get(eid)
    attrs = (node or {}).get("attributes") or {}
    env = beam_own.get("envelope") or {}
    lr = (beam_own.get("leader_results") or {}).get(eid) or {}

    tip = None
    tail = None
    try:
        tip = (float(attrs["tip_x"]), float(attrs["tip_y"]))
    except Exception:
        tip = None
    try:
        tail = (float(attrs["tail_x"]), float(attrs["tail_y"]))
    except Exception:
        # fallback from leader_audit
        ls = (leader_audit or {}).get("leader_start")
        if isinstance(ls, (list, tuple)) and len(ls) >= 2:
            try:
                tail = (float(ls[0]), float(ls[1]))
            except Exception:
                tail = None
    if tip is None:
        lt = (leader_audit or {}).get("leader_tip") or (leader_audit or {}).get("leader_end")
        if isinstance(lt, (list, tuple)) and len(lt) >= 2:
            try:
                tip = (float(lt[0]), float(lt[1]))
            except Exception:
                tip = None

    length = attrs.get("leader_length")
    if length is None:
        length = (leader_audit or {}).get("chain_length")
    orientation = attrs.get("tip_direction") or (leader_audit or {}).get("leader_direction")

    pointed = _pointed_bars(edges, eid)
    anns = _associated_annotations(edges, eid)
    # associated bar = first PhysicalBar / BAR:: / OWN:: target
    assoc_bar = None
    for pid in pointed:
        n = nodes.get(pid) or {}
        if n.get("type") in ("PhysicalBar", "OwnedEntity") or str(pid).startswith(
            ("BAR::", "OWN::")
        ):
            assoc_bar = pid
            break
    if assoc_bar is None and pointed:
        assoc_bar = pointed[0]

    bar_dist = None
    if tip and assoc_bar:
        ba = (nodes.get(assoc_bar) or {}).get("attributes") or {}
        try:
            if "y_position" in ba and "start_x" in ba:
                bx = 0.5 * (float(ba["start_x"]) + float(ba.get("end_x", ba["start_x"])))
                by = float(ba["y_position"])
                bar_dist = round(((tip[0] - bx) ** 2 + (tip[1] - by) ** 2) ** 0.5, 3)
        except Exception:
            bar_dist = None

    concrete = as_bbox(env.get("concrete_envelope"))
    crop = as_bbox(env.get("crop_extent"))
    tip_to_env = dist_point_to_bbox(tip, concrete) if tip and concrete else None
    if tip_to_env is None:
        tip_to_env = qa43_row.get("min_distance_to_production_envelope")
        if tip_to_env is None and leader_audit:
            tip_to_env = leader_audit.get("terminal_distance_to_production_envelope")

    tip_to_support = None
    support_hit = None
    if tip:
        for i, z in enumerate(env.get("support_zones") or []):
            zb = as_bbox(z)
            d = dist_point_to_bbox(tip, zb)
            if d is not None and (tip_to_support is None or d < tip_to_support):
                tip_to_support = d
                support_hit = i

    # Exact existing tip_in_envelope condition (read-only)
    r2_ok = None
    r2_reason = None
    if tip and env.get("concrete_envelope"):
        r2_ok, r2_reason = tip_in_envelope(tip[0], tip[1], env)
    else:
        r2_ok = False
        r2_reason = lr.get("ownership_reason") or "leader_missing_tip_or_envelope"

    # Reproduce evaluate_leader with production pointed bar acceptance if available
    pointed_bar_result = None
    if assoc_bar:
        br = (beam_own.get("bar_results") or {}).get(assoc_bar)
        if br is None:
            # OwnedEntity may be absent from bar_results
            pointed_bar_result = None
        else:
            pointed_bar_result = br
    eval_replay = None
    if node and env.get("concrete_envelope"):
        eval_replay = evaluate_leader(node, env, pointed_bar_result)

    # Nearest competing beam by tip distance to other production envelopes
    nearest_comp = None
    nearest_comp_dist = None
    inside_other = []
    for ob in priority_beams:
        if ob == bid:
            continue
        oenv = all_envelopes.get(ob) or {}
        obox = as_bbox(oenv.get("concrete_envelope")) or as_bbox(oenv.get("crop_extent"))
        d = dist_point_to_bbox(tip, obox)
        if d is not None and (nearest_comp_dist is None or d < nearest_comp_dist):
            nearest_comp_dist = d
            nearest_comp = ob
        if tip and obox:
            x0, y0, x1, y1 = obox
            if x0 <= tip[0] <= x1 and y0 <= tip[1] <= y1:
                inside_other.append(ob)

    env_audit = (qa41_row or {}).get("envelope_audit") or {}
    flags = dict(qa43_row.get("evidence_flags") or {})
    # Prefer QA.4.3 boolean fields
    for k in (
        "leader_chain_continuity",
        "leader_to_bar_proximity",
        "target_beam_context",
        "endpoint_near_envelope",
        "neighbour_ambiguity",
        "inside_other_beam_envelope",
        "longitudinal_overlap",
        "transverse_alignment",
        "beam_axis_alignment",
    ):
        if qa43_row.get(k) is not None:
            flags[k] = qa43_row.get(k)

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "beam_id": bid,
        "leader_id": eid,
        "entity_id": eid,
        "stable_key": stable,
        "entity_type": qa43_row.get("entity_type"),
        "leader_start_point": list(tail) if tail else None,
        "leader_end_point_tip": list(tip) if tip else None,
        "leader_length": _null(length),
        "leader_orientation": _null(orientation),
        "leader_chain_id": eid if str(eid).startswith("LDR::") else None,
        "parent_leader": eid if str(eid).startswith("LDR::") else qa43_row.get("parent_leader_id"),
        "child_leaders": [],
        "associated_bar": assoc_bar,
        "pointed_targets": pointed,
        "bar_distance": bar_dist,
        "target_annotation": anns[0] if anns else None,
        "associated_annotations": anns,
        "target_beam": bid,
        "production_envelope": list(concrete) if concrete else None,
        "crop_extent": list(crop) if crop else None,
        "support_geometry": env.get("support_zones"),
        "distance_tip_to_envelope": tip_to_env,
        "distance_tip_to_support": tip_to_support,
        "nearest_support_zone_index": support_hit,
        "longitudinal_overlap": bool(flags.get("longitudinal_overlap")),
        "transverse_alignment": bool(flags.get("transverse_alignment")),
        "beam_axis_alignment": bool(flags.get("beam_axis_alignment")),
        "target_beam_context": bool(flags.get("target_beam_context")),
        "neighbour_ambiguity": bool(flags.get("neighbour_ambiguity")),
        "inside_other_beam_envelope": bool(
            flags.get("inside_other_beam_envelope") or inside_other
        ),
        "inside_other_beam_ids": inside_other,
        "nearest_competing_beam": nearest_comp,
        "distance_to_competing_beam": nearest_comp_dist,
        "existing_t18_score": lr.get("ownership_score", qa43_row.get("existing_ownership_score")),
        "existing_t18_decision": (
            "ACCEPTED"
            if lr.get("accepted")
            else "REJECTED"
            if lr
            else qa43_row.get("final_ownership_decision")
        ),
        "existing_ownership_reason": lr.get("ownership_reason")
        or qa43_row.get("ownership_reason"),
        "existing_rejected_rule": lr.get("rejected_rule") or qa43_row.get("rejected_rule"),
        "r2_tip_in_envelope_ok": r2_ok,
        "exact_r2_rejection_condition": None if r2_ok else r2_reason,
        "evaluate_leader_replay": eval_replay,
        "graph_node_found": node is not None,
        "recovery_eligible": bool(qa43_row.get("recovery_eligible")),
        "recovery_potential": qa43_row.get("recovery_potential"),
        "spatial_relationship": qa43_row.get("spatial_relationship")
        or env_audit.get("spatial_relationship"),
        "points_toward_target_beam": qa43_row.get("points_toward_target_beam")
        if qa43_row.get("points_toward_target_beam") is not None
        else (leader_audit or {}).get("points_toward_target_beam"),
        "failure_class": qa43_row.get("failure_class")
        or (leader_audit or {}).get("failure_class"),
        "evidence_flags": flags,
    }
