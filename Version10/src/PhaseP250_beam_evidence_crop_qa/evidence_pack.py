"""
Build deterministic Beam Evidence Packages from existing artefacts.
MODEL_VERSION: 10.6.2
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .config import BASE_MARGIN_MM, EVIDENCE_PAD_MM, MAX_EXPAND_ITERS, BBox
from .evidence_window import (
    as_bbox,
    beam_base_bbox,
    evidence_bboxes,
    expand_window_to_evidence,
    object_bbox_from_node,
)
from .owned_geometry import (
    collect_accepted_owned_geometry,
    owned_geometry_bboxes,
)

MODEL_VERSION = "10.6.2"


def _graph_nodes_for_beam(bundle: Any, beam_id: str) -> Dict[str, List[Dict[str, Any]]]:
    nodes = bundle.annotation_graph.get("nodes") or []
    out: Dict[str, List[Dict[str, Any]]] = {
        "PhysicalBar": [],
        "Leader": [],
        "LeaderArrow": [],
        "Annotation": [],
        "Beam": [],
        "OwnedEntity": [],
        "Other": [],
    }
    for n in nodes:
        if (n.get("beam_id") or "") != beam_id and not str(n.get("id") or "").endswith(
            f"::{beam_id}"
        ):
            # also allow BEAM::Bxx
            if n.get("type") == "Beam" and (
                n.get("id") == f"BEAM::{beam_id}"
                or (n.get("attributes") or {}).get("beam_id") == beam_id
            ):
                out["Beam"].append(n)
            continue
        t = n.get("type") or "Other"
        out.setdefault(t, [])
        if t in out:
            out[t].append(n)
        else:
            out["Other"].append(n)
    # bars_by_beam index is authoritative for PhysicalBar
    out["PhysicalBar"] = list(bundle.bars_by_beam.get(beam_id) or out["PhysicalBar"])
    return out


def _accepted_annotation_ids(own: Dict[str, Any]) -> Set[str]:
    ids: Set[str] = set()
    for a in own.get("accepted_annotations") or []:
        aid = a.get("id") or a.get("annotation_id")
        if aid:
            ids.add(str(aid))
    for ch in own.get("accepted_chains") or []:
        aid = ch.get("annotation_id")
        if aid:
            ids.add(str(aid))
    return ids


def _leader_ids_from_ownership(own: Dict[str, Any]) -> Set[str]:
    """Accepted leaders only — rejected T18 leaders must not expand the crop."""
    ids: Set[str] = set()
    raw = own.get("leader_results") or {}
    if isinstance(raw, dict):
        for lid, res in raw.items():
            if isinstance(res, dict) and res.get("accepted"):
                ids.add(str(lid))
            elif not isinstance(res, dict):
                ids.add(str(lid))
    else:
        for lid in raw:
            if isinstance(lid, str):
                ids.add(lid)
            elif isinstance(lid, dict):
                i = lid.get("id") or lid.get("leader_id")
                if i and lid.get("accepted", True):
                    ids.add(str(i))
    for ch in own.get("accepted_chains") or []:
        for lid in ch.get("leaders") or []:
            ids.add(str(lid))
    return ids


def _bar_ids_from_ownership(own: Dict[str, Any]) -> Set[str]:
    """
    Accepted bars only.

    T18 stores all candidate bars in bar_results, including those rejected by
    R5 (e.g. bar_y_outside_reinforcement_elevation). Including rejected bars
    in the evidence window caused extreme crop expansion (P2.5.0.1 / B97A,B98A).
    """
    ids: Set[str] = set()
    raw = own.get("bar_results") or {}
    if isinstance(raw, dict):
        for bid, res in raw.items():
            if isinstance(res, dict) and res.get("accepted"):
                ids.add(str(bid))
            elif not isinstance(res, dict):
                ids.add(str(bid))
    else:
        for bid in raw:
            if isinstance(bid, str):
                ids.add(bid)
            elif isinstance(bid, dict):
                i = bid.get("id") or bid.get("bar_id")
                if i and bid.get("accepted", True):
                    ids.add(str(i))
    for ch in own.get("accepted_chains") or []:
        for d in ch.get("describes") or []:
            if str(d).startswith("BAR::"):
                ids.add(str(d))
    return ids


def _rejected_bar_ids(own: Dict[str, Any]) -> Set[str]:
    raw = own.get("bar_results") or {}
    if not isinstance(raw, dict):
        return set()
    return {
        str(bid)
        for bid, res in raw.items()
        if isinstance(res, dict) and not res.get("accepted")
    }


def _rejected_leader_ids(own: Dict[str, Any]) -> Set[str]:
    raw = own.get("leader_results") or {}
    if not isinstance(raw, dict):
        return set()
    return {
        str(lid)
        for lid, res in raw.items()
        if isinstance(res, dict) and not res.get("accepted")
    }


def _build_relationships(
    *,
    beam_id: str,
    annotations: List[Dict[str, Any]],
    leaders: List[Dict[str, Any]],
    bars: List[Dict[str, Any]],
    owned: List[Dict[str, Any]],
    chains: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rels: List[Dict[str, Any]] = []
    for b in bars:
        rels.append(
            {
                "type": "beam_owns_reinforcement",
                "beam_id": beam_id,
                "reinforcement_id": b.get("id"),
                "basis": "AnnotationGraph.beam_id / ownership.bar_results",
            }
        )
    for og in owned:
        rels.append(
            {
                "type": "beam_owns_owned_geometry",
                "beam_id": beam_id,
                "ownership_id": og.get("ownership_id"),
                "evidence_id": og.get("evidence_id"),
                "basis": "T18.accepted_chains→OWN visual evidence (P2.5.0.3)",
            }
        )
        if og.get("annotation_id") and og.get("leader_id"):
            rels.append(
                {
                    "type": "annotation_leader_owned_geometry",
                    "annotation_id": og.get("annotation_id"),
                    "leader_id": og.get("leader_id"),
                    "ownership_id": og.get("ownership_id"),
                    "source_entity_handle": og.get("source_handle"),
                    "basis": "accepted_chain describes OWN",
                }
            )
        if og.get("leader_id"):
            rels.append(
                {
                    "type": "leader_to_owned_geometry",
                    "leader_id": og.get("leader_id"),
                    "ownership_id": og.get("ownership_id"),
                    "basis": "T18.accepted_chains.describes",
                }
            )
    for a in annotations:
        rels.append(
            {
                "type": "beam_owns_annotation",
                "beam_id": beam_id,
                "annotation_id": a.get("id"),
                "basis": "T18.accepted_annotations",
            }
        )
    for ch in chains:
        aid = ch.get("annotation_id")
        for lid in ch.get("leaders") or []:
            rels.append(
                {
                    "type": "leader_to_annotation",
                    "leader_id": lid,
                    "annotation_id": aid,
                    "basis": "T18.accepted_chains",
                }
            )
        for d in ch.get("describes") or []:
            if str(d).startswith("BAR::"):
                for lid in ch.get("leaders") or []:
                    rels.append(
                        {
                            "type": "leader_to_reinforcement",
                            "leader_id": lid,
                            "reinforcement_id": d,
                            "basis": "T18.accepted_chains.describes",
                        }
                    )
            if str(d).startswith("ANN"):
                continue
    leader_ids = {l.get("id") for l in leaders}
    for l in leaders:
        for r in l.get("relationships") or []:
            if r.get("type") == "POINTS_TO" and r.get("direction") == "out":
                other = r.get("other_id")
                if other and str(other).startswith("BAR::"):
                    rels.append(
                        {
                            "type": "leader_to_reinforcement",
                            "leader_id": l.get("id"),
                            "reinforcement_id": other,
                            "basis": f"graph:{r.get('reason') or 'POINTS_TO'}",
                        }
                    )
    _ = leader_ids
    return rels


def build_beam_evidence_pack(
    *,
    beam_id: str,
    bundle: Any,
    registry_entry: Optional[Dict[str, Any]] = None,
    neighbour_beam_ids: Optional[Sequence[str]] = None,
    base_margin_mm: float = BASE_MARGIN_MM,
    evidence_pad_mm: float = EVIDENCE_PAD_MM,
    max_expand_iters: int = MAX_EXPAND_ITERS,
    msp: Any = None,
    handle_index: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    own = (bundle.beam_ownership.get("by_beam") or {}).get(beam_id) or {}
    env = {}
    if bundle.geometry_envelopes:
        env = (bundle.geometry_envelopes.get("by_beam") or {}).get(beam_id) or {}
    crop_ext = None
    if own.get("envelope"):
        crop_ext = (own["envelope"] or {}).get("crop_extent")
    base = beam_base_bbox(
        envelope_extent=env.get("extent"),
        ownership_crop=crop_ext,
        registry_bbox=(registry_entry or {}).get("bbox"),
        base_margin_mm=base_margin_mm,
    )

    g = _graph_nodes_for_beam(bundle, beam_id)
    accepted_ann_ids = _accepted_annotation_ids(own)
    leader_ids = _leader_ids_from_ownership(own)
    bar_ids = _bar_ids_from_ownership(own)
    rejected_bar_ids = _rejected_bar_ids(own)
    rejected_leader_ids = _rejected_leader_ids(own)

    # Accepted-only reinforcement. Never fall back to all graph bars for the beam —
    # that pulled in T18-rejected far-elevation bars and exploded the crop.
    if bar_ids:
        bars = [n for n in g["PhysicalBar"] if n.get("id") in bar_ids]
    else:
        bars = []

    if leader_ids:
        leaders = [n for n in g["Leader"] if n.get("id") in leader_ids]
    else:
        leaders = []
    graph_anns_by_id = {
        n.get("id"): n
        for n in (bundle.annotation_graph.get("nodes") or [])
        if n.get("type") == "Annotation"
    }
    annotations: List[Dict[str, Any]] = []
    for a in own.get("accepted_annotations") or []:
        aid = a.get("id") or a.get("annotation_id")
        gn = graph_anns_by_id.get(aid) if aid else None
        rec = {
            "id": aid,
            "type": "Annotation",
            "beam_id": beam_id,
            "text": a.get("text") or (gn or {}).get("attributes", {}).get("clean_text"),
            "attributes": dict((gn or {}).get("attributes") or {}),
            "ownership_reason": a.get("ownership_reason"),
            "accepted": True,
            "source": "T18.accepted_annotations",
        }
        if gn:
            rec["attributes"].setdefault("x", (gn.get("attributes") or {}).get("x"))
            rec["attributes"].setdefault("y", (gn.get("attributes") or {}).get("y"))
            rec["relationships"] = gn.get("relationships") or []
        annotations.append(rec)

    chains = list(own.get("accepted_chains") or [])
    rejected_chains = list(own.get("rejected_chains") or [])

    owned = collect_accepted_owned_geometry(
        beam_id=beam_id,
        ownership=own,
        annotation_graph=bundle.annotation_graph or {},
        msp=msp,
        handle_index=handle_index,
    )

    # Leader-chain completeness: annotation + leader + (PhysicalBar OR OWN geometry)
    complete_chains = []
    incomplete_chains = []
    for ch in chains:
        lids = ch.get("leaders") or []
        describes = ch.get("describes") or []
        has_bar = any(str(d).startswith("BAR::") for d in describes)
        has_own = any(str(d).startswith("OWN::") for d in describes)
        if lids and ch.get("annotation_id") and (has_bar or has_own):
            complete_chains.append(ch)
        else:
            incomplete_chains.append(ch)

    eboxes = evidence_bboxes(bars=bars, leaders=leaders, annotations=annotations)
    for a in annotations:
        bb = object_bbox_from_node(a)
        if bb:
            eboxes.append(bb)
    # P2.5.0.3: accepted OWN TOP_BAR geometry expands the window (not rejected BARs)
    eboxes.extend(owned_geometry_bboxes(owned))

    expansion = {
        "expansions": 0,
        "clipped_before_count": 0,
        "still_clipped_count": 0,
        "border_touch_count": 0,
        "expanded": False,
    }
    evidence_window: Optional[BBox] = base
    if base:
        evidence_window, expansion = expand_window_to_evidence(
            base,
            eboxes,
            pad_mm=evidence_pad_mm,
            max_iters=max_expand_iters,
        )

    relationships = _build_relationships(
        beam_id=beam_id,
        annotations=annotations,
        leaders=leaders,
        bars=bars,
        owned=owned,
        chains=chains,
    )

    neighbours = list(neighbour_beam_ids or [])
    shared_scopes = []
    for sc in (bundle.engineering_scopes.get("scopes") or []):
        members = sc.get("member_beams") or []
        if beam_id in members:
            shared_scopes.append(
                {
                    "scope_id": sc.get("scope_id"),
                    "scope_type": sc.get("scope_type"),
                    "member_beams": members,
                    "annotation_text": sc.get("annotation_text"),
                    "shared": True,
                }
            )

    _ = accepted_ann_ids

    return {
        "model_version": MODEL_VERSION,
        "phase_id": "P2.5.0",
        "beam_id": beam_id,
        "target_beam": {
            "beam_id": beam_id,
            "bbox": list(base) if base else None,
            "envelope_extent": env.get("extent"),
            "crop_extent_t18": crop_ext,
            "orientation": env.get("orientation"),
            "depth_mm": env.get("depth_mm"),
            "in_ownership": bool(own),
            "in_envelope": bool(env),
        },
        "evidence_window": {
            "bbox": list(evidence_window) if evidence_window else None,
            "base_bbox": list(base) if base else None,
            "expansion": expansion,
            "coordinate_space": "DXF_MODEL_MM",
        },
        "annotations": [
            {
                "annotation_id": a.get("id"),
                "raw_text": a.get("text"),
                "normalized_text": (a.get("attributes") or {}).get("clean_text"),
                "position": {
                    "x": (a.get("attributes") or {}).get("x"),
                    "y": (a.get("attributes") or {}).get("y"),
                },
                "bbox": list(object_bbox_from_node(a) or []) or None,
                "source": a.get("source"),
            }
            for a in annotations
        ],
        "leaders": [
            {
                "leader_id": l.get("id"),
                "geometry": {
                    "tip_x": (l.get("attributes") or {}).get("tip_x"),
                    "tip_y": (l.get("attributes") or {}).get("tip_y"),
                    "tail_x": (l.get("attributes") or {}).get("tail_x"),
                    "tail_y": (l.get("attributes") or {}).get("tail_y"),
                },
                "bbox": list(object_bbox_from_node(l) or []) or None,
                "source": "AnnotationGraph+T18",
            }
            for l in leaders
        ],
        "reinforcement": [
            {
                "reinforcement_id": b.get("id"),
                "entity_handle": (b.get("attributes") or {}).get("dxf_handle"),
                "entity_type": (b.get("attributes") or {}).get("entity_type"),
                "geometry": {
                    "start_x": (b.get("attributes") or {}).get("start_x"),
                    "end_x": (b.get("attributes") or {}).get("end_x"),
                    "y_position": (b.get("attributes") or {}).get("y_position"),
                    "vertical_placement": (b.get("attributes") or {}).get(
                        "vertical_placement"
                    ),
                },
                "bbox": list(object_bbox_from_node(b) or []) or None,
                "candidate_role": (b.get("attributes") or {}).get("vertical_placement"),
                "diameter": "UNKNOWN",
                "source": b.get("source") or "AnnotationGraph",
            }
            for b in bars
        ],
        "owned_geometry": owned,
        "relationships": relationships,
        "leader_chains": {
            "accepted": chains,
            "rejected": rejected_chains,
            "complete_count": len(complete_chains),
            "incomplete_count": len(incomplete_chains),
            "complete": complete_chains,
            "incomplete": incomplete_chains,
        },
        "neighbours": neighbours,
        "shared_scopes": shared_scopes,
        "counts": {
            "annotations": len(annotations),
            "leaders": len(leaders),
            "reinforcement": len(bars),
            "owned_geometry": len(owned),
            "owned_top_bar": sum(
                1 for o in owned if o.get("evidence_type") == "OWN_TOP_BAR"
            ),
            "relationships": len(relationships),
            "complete_chains": len(complete_chains),
            "rejected_bars_excluded": len(rejected_bar_ids),
            "rejected_leaders_excluded": len(rejected_leader_ids),
        },
        "excluded_rejected_evidence": {
            "bars": sorted(rejected_bar_ids),
            "leaders": sorted(rejected_leader_ids),
            "basis": (
                "T18 bar_results/leader_results with accepted=false are diagnostic "
                "candidates only and must not expand the P2.5.0 evidence window "
                "(P2.5.0.1 fix). Accepted OWN::TOP_BAR geometry is separate visual "
                "evidence (P2.5.0.3) and does not re-include rejected PhysicalBars."
            ),
        },
    }
