"""
Per-entity dropped recovery audit (diagnostic only).
MODEL_VERSION: 10.5.0
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .geometry_helpers import (
    ANN_REACH_DEPTH_FACTOR,
    SUPPORT_EXT_MM,
    as_bbox,
    axis_metrics,
    dist_point_to_bbox,
    entity_bounds_from_attrs,
    entity_point_from_attrs,
    longitudinal_overlap,
    point_in_bbox,
    spatial_class,
)

MODEL_VERSION = "10.5.0"

AUDIT_CAT = {
    "SEARCH_ENVELOPE_FAILURE": "ENVELOPE_NEVER_CANDIDATE",
    "LEADER_FAILURE": "LEADER_CHAIN_FAILURE",
    "GEOMETRY_FAILURE": "GEOMETRY_FAILURE",
    "CONFLICT_FAILURE": "OTHER_UNKNOWN",
    "OWNED_ELSEWHERE": "OTHER_UNKNOWN",
    "UNKNOWN": "OTHER_UNKNOWN",
}


def _node_index(graph_doc: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    idx: Dict[str, Dict[str, Any]] = {}
    if not graph_doc:
        return idx
    for n in graph_doc.get("nodes") or []:
        if n.get("id"):
            idx[str(n["id"])] = n
    return idx


def _envelope_for_beam(own_by_beam: Dict[str, Any], beam_id: str) -> Dict[str, Any]:
    return ((own_by_beam.get(beam_id) or {}).get("envelope") or {})


def _production_envelope(env: Dict[str, Any]) -> Tuple[Optional[tuple], str]:
    concrete = as_bbox(env.get("concrete_envelope"))
    if concrete:
        return concrete, "concrete_envelope"
    crop = as_bbox(env.get("crop_extent"))
    if crop:
        return crop, "crop_extent"
    reach = as_bbox(env.get("annotation_reach"))
    return reach, "annotation_reach" if reach else "missing"


def map_audit_category(qa34_category: Optional[str], reason: Optional[str]) -> str:
    if qa34_category in AUDIT_CAT:
        return AUDIT_CAT[qa34_category]
    r = (reason or "").lower()
    if "never" in r or "candidate" in r or "envelope" in r:
        return "ENVELOPE_NEVER_CANDIDATE"
    if "leader" in r or "chain" in r or "tip" in r:
        return "LEADER_CHAIN_FAILURE"
    if "outside" in r or "geometry" in r or "bar_" in r:
        return "GEOMETRY_FAILURE"
    return "OTHER_UNKNOWN"


def audit_envelope(
    *,
    beam_id: str,
    pt: Optional[tuple],
    bounds: Optional[tuple],
    env: Dict[str, Any],
    all_envelopes: Dict[str, Dict[str, Any]],
    priority_beams: Sequence[str],
) -> Dict[str, Any]:
    prod, prod_src = _production_envelope(env)
    crop = as_bbox(env.get("crop_extent"))
    depth = float(env.get("depth_mm") or 600.0)
    dist = dist_point_to_bbox(pt, prod)
    inside = point_in_bbox(pt, prod, pad=0.0)
    # boundary if within 1mm
    on_boundary = (not inside) and dist is not None and dist <= 1.0
    if inside:
        # refine boundary: near edge
        if dist is not None and dist <= 1.0:
            on_boundary = True
            inside = True
    sp = spatial_class(dist, inside=bool(inside), on_boundary=bool(on_boundary), depth_mm=depth)
    ax = axis_metrics(pt, env.get("centreline"), crop)
    long_overlap = longitudinal_overlap(pt, crop)

    # endpoint distances if bounds exist
    endpoint_dists = {}
    if bounds:
        corners = [
            (bounds[0], bounds[1]),
            (bounds[0], bounds[3]),
            (bounds[2], bounds[1]),
            (bounds[2], bounds[3]),
        ]
        endpoint_dists = {
            f"corner_{i}": dist_point_to_bbox(c, prod) for i, c in enumerate(corners)
        }

    # neighbour envelope occupancy
    nearer = []
    inside_other = []
    for bid in priority_beams:
        if bid == beam_id:
            continue
        oenv = all_envelopes.get(bid) or {}
        obox, _ = _production_envelope(oenv)
        d = dist_point_to_bbox(pt, obox)
        if d is not None:
            nearer.append({"beam_id": bid, "distance": d})
        if point_in_bbox(pt, obox):
            inside_other.append(bid)
    nearer.sort(key=lambda x: x["distance"])
    nearest = nearer[0] if nearer else None
    closer_to_neighbour = bool(
        nearest
        and dist is not None
        and nearest["distance"] is not None
        and nearest["distance"] + 1e-6 < dist
    )

    # recovery potential
    flags = {
        "near_production_envelope": sp == "NEAR_OUTSIDE",
        "endpoint_near_envelope": any(
            (v is not None and v <= SUPPORT_EXT_MM) for v in endpoint_dists.values()
        )
        if endpoint_dists
        else False,
        "beam_axis_alignment": (ax.get("beam_axis_distance") or 1e9)
        <= max(depth * 0.5, SUPPORT_EXT_MM),
        "longitudinal_overlap": long_overlap,
        "transverse_alignment": (ax.get("transverse_projection") or 1e9)
        <= depth * ANN_REACH_DEPTH_FACTOR,
        "target_beam_context": long_overlap and sp in ("NEAR_OUTSIDE", "BOUNDARY", "INSIDE"),
        "neighbour_ambiguity": closer_to_neighbour or bool(inside_other),
        "inside_other_beam_envelope": bool(inside_other),
    }
    if sp in ("NEAR_OUTSIDE", "BOUNDARY") and flags["longitudinal_overlap"] and not flags["neighbour_ambiguity"]:
        potential = "HIGH"
    elif sp in ("NEAR_OUTSIDE", "MODERATE_OUTSIDE") and flags["longitudinal_overlap"]:
        potential = "MEDIUM"
    elif sp == "FAR_OUTSIDE" or flags["neighbour_ambiguity"]:
        potential = "LOW"
    elif pt is None:
        potential = "UNKNOWN"
    else:
        potential = "MEDIUM" if flags["longitudinal_overlap"] else "LOW"

    return {
        "production_envelope_source": prod_src,
        "production_envelope": list(prod) if prod else None,
        "crop_extent": list(crop) if crop else None,
        "entity_centroid": list(pt) if pt else None,
        "entity_bounds": list(bounds) if bounds else None,
        "min_distance_to_production_envelope": dist,
        "endpoint_distances": endpoint_dists,
        "intersects_envelope": bool(inside),
        "touches_boundary": bool(on_boundary),
        "spatial_relationship": sp,
        "depth_mm": depth,
        "diagnostic_bands": {
            "near_mm": SUPPORT_EXT_MM,
            "moderate_mm": max(SUPPORT_EXT_MM, depth * ANN_REACH_DEPTH_FACTOR),
            "note": "Bands use existing T18 SUPPORT_EXT_MM and ANN_REACH_DEPTH_FACTOR; no new production thresholds",
        },
        **ax,
        "longitudinal_overlap": long_overlap,
        "nearest_neighbour": nearest,
        "closer_to_neighbour": closer_to_neighbour,
        "inside_other_beam_envelopes": inside_other,
        "evidence_flags": flags,
        "recovery_potential": potential,
    }


def audit_leader(
    *,
    entity_id: str,
    beam_id: str,
    node: Optional[Dict[str, Any]],
    graph_idx: Dict[str, Dict[str, Any]],
    env: Dict[str, Any],
    reason: Optional[str],
    text: Optional[str],
) -> Dict[str, Any]:
    attrs = (node or {}).get("attributes") or {}
    tip = None
    tail = None
    try:
        tip = (float(attrs["tip_x"]), float(attrs["tip_y"]))
    except Exception:
        tip = None
    try:
        tail = (float(attrs["tail_x"]), float(attrs["tail_y"]))
    except Exception:
        tail = None

    prod, _ = _production_envelope(env)
    tip_dist = dist_point_to_bbox(tip, prod)
    # Best-effort linked annotation lookup from graph (relationships may be dict or list)
    ann_id = None
    ann_text = text
    for n in graph_idx.values():
        if n.get("type") != "Annotation":
            continue
        if str(n.get("beam_id") or "") not in ("", beam_id) and str(n.get("beam_id")) != beam_id:
            continue
        rel = n.get("relationships")
        leader_ids = []
        if isinstance(rel, dict):
            leader_ids = list(rel.get("leaders") or [])
        elif isinstance(rel, list):
            for item in rel:
                if isinstance(item, dict) and item.get("type") in ("Leader", "leader"):
                    if item.get("id"):
                        leader_ids.append(item["id"])
                elif isinstance(item, str) and item.startswith("LDR::"):
                    leader_ids.append(item)
        attr_leaders = (n.get("attributes") or {}).get("leaders")
        if isinstance(attr_leaders, list):
            leader_ids.extend(attr_leaders)
        if entity_id in leader_ids or any(str(x) == entity_id for x in leader_ids):
            ann_id = n.get("id")
            ann_text = ann_text or (n.get("attributes") or {}).get("text") or n.get("text")
            break

    tip_dir = attrs.get("tip_direction")
    centreline = env.get("centreline") or {}
    points_to_beam = None
    if tip and tail:
        # vector tip-tail; if tip closer to envelope than tail → pointing toward beam zone
        tail_dist = dist_point_to_bbox(tail, prod)
        if tip_dist is not None and tail_dist is not None:
            points_to_beam = tip_dist <= tail_dist

    r = (reason or "").lower()
    if "tip_outside" in r or "outside_envelope" in r:
        fail = "LEADER_TIP_OUTSIDE"
    elif "non_owned" in r or "points_to" in r:
        fail = "LEADER_TARGET_AMBIGUOUS"
    elif "missing" in r or "incomplete" in r:
        fail = "LEADER_CHAIN_INCOMPLETE"
    elif "neighbour" in r:
        fail = "LEADER_TARGET_NEIGHBOUR"
    elif "empty" in r:
        fail = "LEADER_TERMINATES_EMPTY"
    elif "disconnect" in r:
        fail = "LEADER_CHAIN_DISCONNECTED"
    else:
        fail = "OTHER"

    flags = {
        "leader_chain_continuity": bool(tip and tail),
        "leader_to_bar_proximity": tip_dist is not None and tip_dist <= SUPPORT_EXT_MM,
        "near_production_envelope": tip_dist is not None and tip_dist <= SUPPORT_EXT_MM,
        "target_beam_context": bool(points_to_beam),
        "neighbour_ambiguity": fail == "LEADER_TARGET_NEIGHBOUR",
    }
    if fail == "LEADER_TIP_OUTSIDE" and tip_dist is not None and tip_dist <= SUPPORT_EXT_MM and points_to_beam:
        potential = "HIGH"
    elif flags["leader_chain_continuity"] and tip_dist is not None and tip_dist <= max(SUPPORT_EXT_MM * 2, 700):
        potential = "MEDIUM"
    elif not tip:
        potential = "UNKNOWN"
    else:
        potential = "LOW"

    return {
        "annotation_text": ann_text,
        "annotation_id": ann_id,
        "leader_id": entity_id if str(entity_id).startswith("LDR::") else attrs.get("leader_id"),
        "leader_start": list(tail) if tail else None,
        "leader_end": list(tip) if tip else None,
        "leader_tip": list(tip) if tip else None,
        "chain_length": attrs.get("leader_length"),
        "leader_segment_count": attrs.get("vertex_count"),
        "chain_continuity": bool(tip and tail),
        "terminal_geometry": list(tip) if tip else None,
        "terminal_distance_to_production_envelope": tip_dist,
        "leader_direction": tip_dir,
        "points_toward_target_beam": points_to_beam,
        "failure_class": fail,
        "evidence_flags": flags,
        "recovery_potential": potential,
        "layer": attrs.get("layer"),
    }


def audit_geometry(
    *,
    attrs: Dict[str, Any],
    bounds: Optional[tuple],
    pt: Optional[tuple],
    env: Dict[str, Any],
    reason: Optional[str],
) -> Dict[str, Any]:
    prod, _ = _production_envelope(env)
    w = h = length = None
    zero_w = zero_h = degenerate = False
    if bounds:
        w = abs(bounds[2] - bounds[0])
        h = abs(bounds[3] - bounds[1])
        length = max(w, h)
        zero_w = w <= 1e-6
        zero_h = h <= 1e-6
        degenerate = zero_w and zero_h
    dist = dist_point_to_bbox(pt, prod)
    r = (reason or "").lower()
    if zero_w and not zero_h:
        gclass = "ZERO_WIDTH"
    elif zero_h and not zero_w:
        gclass = "ZERO_HEIGHT"
    elif degenerate:
        gclass = "DEGENERATE"
    elif "outside" in r or "envelope" in r:
        gclass = "BBOX_MISS"
    elif "endpoint" in r:
        gclass = "ENDPOINT_MISS"
    elif "axis" in r or "orientation" in r:
        gclass = "AXIS_MISMATCH"
    elif "segment" in r or "polyline" in r:
        gclass = "SEGMENT_GEOMETRY"
    else:
        gclass = "OTHER"

    if gclass in ("BBOX_MISS", "ENDPOINT_MISS") and dist is not None and dist <= SUPPORT_EXT_MM:
        potential = "HIGH"
    elif not degenerate and dist is not None and dist <= SUPPORT_EXT_MM * 2:
        potential = "MEDIUM"
    elif degenerate or zero_w or zero_h:
        potential = "LOW"
    else:
        potential = "UNKNOWN" if pt is None else "LOW"

    return {
        "bounding_box": list(bounds) if bounds else None,
        "start_point": None,
        "end_point": None,
        "width": w,
        "height": h,
        "length": length,
        "zero_width": zero_w,
        "zero_height": zero_h,
        "degenerate_geometry": degenerate,
        "segment_count": attrs.get("vertex_count"),
        "min_distance_to_production_envelope": dist,
        "geometry_class": gclass,
        "existing_geometry_rejection_reason": reason,
        "recovery_potential": potential,
        "evidence_flags": {
            "near_production_envelope": dist is not None and dist <= SUPPORT_EXT_MM,
            "degenerate_geometry": degenerate,
        },
    }


def enrich_and_audit_all(
    population_records: List[Dict[str, Any]],
    *,
    beam_ownership: Dict[str, Any],
    graph_doc: Optional[Dict[str, Any]],
    migration: Optional[Dict[str, Any]],
    priority_beams: Sequence[str],
) -> Dict[str, Any]:
    by_beam = (beam_ownership or {}).get("by_beam") or {}
    envelopes = {b: _envelope_for_beam(by_beam, b) for b in priority_beams}
    gidx = _node_index(graph_doc)

    # text owners from migrations / accepted anns for neighbour audit
    text_accepted: Dict[str, List[str]] = defaultdict(list)
    for bid, own in by_beam.items():
        for ann in own.get("accepted_annotations") or []:
            t = " ".join(str(ann.get("text") or "").upper().split())
            if t:
                text_accepted[t].append(bid)

    audits: List[Dict[str, Any]] = []
    envelope_audits = []
    leader_audits = []
    geometry_audits = []
    evidence_rows = []

    for rec in population_records:
        bid = rec["beam_id"]
        eid = rec["entity_id"]
        node = gidx.get(eid)
        attrs = (node or {}).get("attributes") or {}
        pt = entity_point_from_attrs(attrs)
        bounds = entity_bounds_from_attrs(attrs)
        env = envelopes.get(bid) or {}
        audit_cat = map_audit_category(rec.get("qa34_category"), rec.get("original_rejection_reason"))

        # handle from id
        handle = None
        if "::" in eid:
            handle = eid.split("::")[-1]

        layer = attrs.get("layer")
        geom_type = (node or {}).get("type") or rec.get("entity_type")

        env_part = audit_envelope(
            beam_id=bid,
            pt=pt,
            bounds=bounds,
            env=env,
            all_envelopes=envelopes,
            priority_beams=priority_beams,
        )
        leader_part = None
        geom_part = None
        if audit_cat == "LEADER_CHAIN_FAILURE" or rec.get("entity_type") == "Leader":
            leader_part = audit_leader(
                entity_id=eid,
                beam_id=bid,
                node=node,
                graph_idx=gidx,
                env=env,
                reason=rec.get("original_rejection_reason"),
                text=rec.get("text"),
            )
        if audit_cat == "GEOMETRY_FAILURE":
            geom_part = audit_geometry(
                attrs=attrs,
                bounds=bounds,
                pt=pt,
                env=env,
                reason=rec.get("original_rejection_reason"),
            )

        # recovery potential selection by category
        if audit_cat == "ENVELOPE_NEVER_CANDIDATE":
            potential = env_part.get("recovery_potential")
            flags = dict(env_part.get("evidence_flags") or {})
        elif audit_cat == "LEADER_CHAIN_FAILURE":
            potential = (leader_part or {}).get("recovery_potential") or "UNKNOWN"
            flags = dict((leader_part or {}).get("evidence_flags") or {})
            flags.update({k: v for k, v in (env_part.get("evidence_flags") or {}).items() if v})
        elif audit_cat == "GEOMETRY_FAILURE":
            potential = (geom_part or {}).get("recovery_potential") or "UNKNOWN"
            flags = dict((geom_part or {}).get("evidence_flags") or {})
        else:
            potential = "UNKNOWN"
            flags = {}

        nt = " ".join(str(rec.get("text") or "").upper().split()) if rec.get("text") else None
        same_text_elsewhere = [b for b in text_accepted.get(nt or "", []) if b != bid] if nt else []

        row = {
            **rec,
            "entity_layer": layer,
            "entity_handle": handle,
            "geometry_type": geom_type,
            "geometry_bounds": list(bounds) if bounds else None,
            "centroid": list(pt) if pt else None,
            "start_point": (leader_part or {}).get("leader_start"),
            "end_point": (leader_part or {}).get("leader_end") or (leader_part or {}).get("leader_tip"),
            "original_rule_stage": rec.get("rejected_rule") or rec.get("qa34_category"),
            "candidate_status": False if audit_cat == "ENVELOPE_NEVER_CANDIDATE" else True,
            "primary_audit_category": audit_cat,
            "recovery_audit_status": "AUDITED",
            "recovery_potential": potential,
            "evidence_flags": flags,
            "same_annotation_text_on_other_beams": same_text_elsewhere[:10],
            "qa34_recorded_other_owner": False,  # dropped by definition
            "envelope_audit": env_part,
            "leader_audit": leader_part,
            "geometry_audit": geom_part,
            "graph_node_found": node is not None,
        }
        audits.append(row)
        if audit_cat == "ENVELOPE_NEVER_CANDIDATE":
            envelope_audits.append({"stable_key": row["stable_key"], **env_part, "beam_id": bid, "entity_id": eid, "recovery_potential": potential})
        if audit_cat == "LEADER_CHAIN_FAILURE":
            leader_audits.append({"stable_key": row["stable_key"], **(leader_part or {}), "beam_id": bid, "entity_id": eid, "recovery_potential": potential})
        if audit_cat == "GEOMETRY_FAILURE":
            geometry_audits.append({"stable_key": row["stable_key"], **(geom_part or {}), "beam_id": bid, "entity_id": eid, "recovery_potential": potential})
        evidence_rows.append(
            {
                "stable_key": row["stable_key"],
                "beam_id": bid,
                "entity_id": eid,
                "primary_audit_category": audit_cat,
                "recovery_potential": potential,
                "evidence_flags": flags,
            }
        )

    cat_counts = Counter(r["primary_audit_category"] for r in audits)
    pot_counts = Counter(r["recovery_potential"] for r in audits)
    return {
        "audits": audits,
        "envelope_audits": envelope_audits,
        "leader_audits": leader_audits,
        "geometry_audits": geometry_audits,
        "evidence_rows": evidence_rows,
        "category_counts": dict(cat_counts),
        "potential_counts": dict(pot_counts),
        "beam_dropped_counts": dict(Counter(r["beam_id"] for r in audits)),
    }
