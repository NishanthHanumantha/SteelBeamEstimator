"""
Per-beam ownership explainability (Stages 1-6) from persisted artefacts.
MODEL_VERSION: 10.0.3

Does NOT re-run or mutate ownership decisions.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from .geometry_helpers import (
    as_bbox,
    axis_projection,
    dist_to_bbox,
    entity_point,
    envelope_search_bbox,
    point_in_bbox,
    score_breakdown_from_rules,
)

MODEL_VERSION = "10.0.3"

RULE_CATALOGUE = {
    "R1_PHYSICAL_BAR": "PhysicalBar centre inside Beam Envelope",
    "R2_LEADER_TIP": "Leader tip inside Envelope or support extension",
    "R3_ANNOTATION_VIA_CHAIN": "Annotation ownership only via Leader→Bar (or DESCRIBES bar)",
    "R4_SEMANTIC_VIA_ANN": "Semantic inherits only from Annotation",
    "R5_NEIGHBOUR_REJECT": "Reject chain if bar/leader resolves outside envelope / neighbour side",
    "R6_VERTICAL_OWNERSHIP": "PhysicalBar Y in beam reinforcement elevation",
    "R7_LD_SUPPORT_ONLY": "Ld may extend only via support extension",
    "R8_SIDE_FACE_WEB": "Side-face annotation intersects beam web Y",
    "R9_STIRRUP_REGION": "Stirrup annotation intersects stirrup region",
    "R10_CONFIDENCE": "Store ownership_reason / score / accepted_rule",
}


def _by_beam(doc: Optional[Dict[str, Any]], beam_id: str) -> Dict[str, Any]:
    if not doc:
        return {}
    by = doc.get("by_beam") or {}
    if isinstance(by, dict) and beam_id in by:
        return by[beam_id] or {}
    return {}


def _node_index(graph_doc: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    idx: Dict[str, Dict[str, Any]] = {}
    if not graph_doc:
        return idx
    for n in graph_doc.get("nodes") or []:
        nid = n.get("id")
        if nid:
            idx[str(nid)] = n
    return idx


def _nodes_for_beam(
    graph_doc: Optional[Dict[str, Any]], beam_id: str
) -> List[Dict[str, Any]]:
    if not graph_doc:
        return []
    by = (graph_doc.get("by_beam") or {}).get(beam_id)
    if isinstance(by, dict) and "node_ids" in by:
        idx = _node_index(graph_doc)
        return [idx[i] for i in by["node_ids"] if i in idx]
    # Fallback: filter all nodes by beam_id
    out = []
    for n in graph_doc.get("nodes") or []:
        if str(n.get("beam_id") or "") == beam_id:
            out.append(n)
    return out


def _classify_entity_type(node: Dict[str, Any]) -> str:
    t = str(node.get("type") or "")
    if t in ("PhysicalBar", "OwnedEntity"):
        return "Bar"
    if t == "Leader":
        return "Leader"
    if t == "Annotation":
        return "Annotation"
    if t == "SemanticFact":
        return "Semantic"
    if t == "Dimension":
        return "Dimension"
    return t or "Unknown"


def stage1_candidate_discovery(
    beam_id: str,
    own: Dict[str, Any],
    env_geom: Dict[str, Any],
    beam_nodes: List[Dict[str, Any]],
    considered_ids: Set[str],
) -> Dict[str, Any]:
    envelope = own.get("envelope") or {}
    search = envelope_search_bbox(envelope)
    crop = as_bbox(envelope.get("crop_extent") or env_geom.get("extent"))
    centreline = envelope.get("centreline") or {}
    axis = env_geom.get("axis") or {}
    cx = axis.get("centroid_x") or centreline.get("mark_x")
    cy = axis.get("centroid_y") or centreline.get("y") or centreline.get("mark_y")
    try:
        centroid = [float(cx), float(cy)] if cx is not None and cy is not None else None
    except Exception:
        centroid = None

    # Reach / radius diagnostic (existing constants exposed, not new logic)
    depth = float(envelope.get("depth_mm") or env_geom.get("depth_mm") or 0.0)
    ann_reach = as_bbox(envelope.get("annotation_reach"))
    reach_h = (ann_reach[3] - ann_reach[1]) if ann_reach else None

    nearby: List[Dict[str, Any]] = []
    counts = Counter()
    type_buckets = {
        "Bars": 0,
        "Leaders": 0,
        "Annotations": 0,
        "Dimensions": 0,
        "Lines": 0,
        "Polylines": 0,
        "Blocks": 0,
        "Text": 0,
        "MTEXT": 0,
    }

    for node in beam_nodes:
        nid = str(node.get("id") or "")
        et = _classify_entity_type(node)
        attrs = node.get("attributes") or {}
        pt = entity_point(attrs, et)
        inside = point_in_bbox(pt, search, pad=50.0) if search else False
        # Also include if considered by ownership even if geometry missing
        considered = nid in considered_ids
        if not inside and not considered:
            # Still report nodes clearly near crop
            if not point_in_bbox(pt, crop, pad=400.0):
                continue

        proj = axis_projection(pt, centreline)
        dist = dist_to_bbox(pt, search) if search else None

        is_candidate = considered
        if not is_candidate:
            if not inside:
                reason = "Outside search envelope"
            elif et in ("Beam",):
                reason = "Filtered by type"
            else:
                reason = "Not evaluated by ownership filter (not in T18 results)"
        else:
            reason = None

        # Bucket counts for inside envelope
        if inside or considered:
            if et == "Bar":
                type_buckets["Bars"] += 1
            elif et == "Leader":
                type_buckets["Leaders"] += 1
            elif et == "Annotation":
                type_buckets["Annotations"] += 1
                # text-ish
                type_buckets["Text"] += 1
            elif et == "Dimension":
                type_buckets["Dimensions"] += 1

        counts[et] += 1
        nearby.append(
            {
                "entity_id": nid,
                "entity_type": et,
                "distance": dist,
                "projection_onto_beam_axis": proj.get("projection"),
                "perpendicular_offset": proj.get("perpendicular_offset"),
                "orientation": attrs.get("orientation") or axis.get("orientation"),
                "point": list(pt) if pt else None,
                "candidate": is_candidate,
                "reason_if_not_candidate": reason,
                "inside_search_envelope": inside,
            }
        )

    step_pass = search is not None and len(nearby) > 0
    return {
        "beam_id": beam_id,
        "beam_centroid": centroid,
        "beam_axis": axis or centreline,
        "beam_extents": list(crop) if crop else None,
        "ownership_search_envelope": list(search) if search else None,
        "envelope_dimensions": (
            [search[2] - search[0], search[3] - search[1]] if search else None
        ),
        "candidate_search_radius": {
            "annotation_reach_height_mm": reach_h,
            "depth_mm": depth,
            "ann_reach_depth_factor": 4.0,
            "support_ext_mm": 350.0,
            "note": "Constants from T18 beam_envelope (exposed, not recomputed)",
        },
        "search_method": "T18 Beam Ownership Envelope (crop U concrete U annotation_reach)",
        "side_of_mark": envelope.get("side_of_mark"),
        "body_reason": envelope.get("body_reason"),
        "envelope_zones": {
            "crop_extent": envelope.get("crop_extent"),
            "concrete_envelope": envelope.get("concrete_envelope"),
            "annotation_reach": envelope.get("annotation_reach"),
            "support_zones": envelope.get("support_zones"),
            "stirrup_region": envelope.get("stirrup_region"),
        },
        "inside_envelope_counts": type_buckets,
        "nearby_entities": nearby,
        "nearby_count": len(nearby),
        "candidate_count": sum(1 for e in nearby if e["candidate"]),
        "status": "PASS" if step_pass else "FAIL",
    }


def stage2_scoring(
    beam_id: str,
    own: Dict[str, Any],
    t16_ents: List[Dict[str, Any]],
) -> Dict[str, Any]:
    scored: List[Dict[str, Any]] = []

    def _add(entity_id: str, entity_type: str, result: Dict[str, Any], source: str) -> None:
        bd = score_breakdown_from_rules(
            result.get("accepted_rules"),
            result.get("rejected_rule"),
            result.get("ownership_score"),
        )
        scored.append(
            {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "source": source,
                "accepted": bool(result.get("accepted")),
                "ownership_reason": result.get("ownership_reason"),
                "accepted_rules": result.get("accepted_rules") or [],
                "rejected_rule": result.get("rejected_rule"),
                "raw_score": result.get("ownership_score"),
                "normalised_score": result.get("ownership_score"),
                "total_ownership_score": result.get("ownership_score"),
                "score_breakdown": bd,
                "rule_meanings": {
                    r: RULE_CATALOGUE.get(r, r)
                    for r in (result.get("accepted_rules") or [])
                    if r
                },
                "rejected_rule_meaning": RULE_CATALOGUE.get(
                    result.get("rejected_rule") or "", result.get("rejected_rule")
                ),
            }
        )

    for nid, res in (own.get("bar_results") or {}).items():
        _add(str(nid), "Bar", res or {}, "T18.bar_results")
    for nid, res in (own.get("leader_results") or {}).items():
        _add(str(nid), "Leader", res or {}, "T18.leader_results")
    for ann in (own.get("accepted_annotations") or []) + (
        own.get("rejected_annotations") or []
    ):
        item = dict(ann)
        # Expose neighbour hint already persisted by T18 (not a new decision)
        if ann.get("neighbour_beam_source"):
            item["neighbour_beam_source"] = ann.get("neighbour_beam_source")
        _add(str(ann.get("id")), "Annotation", item, "T18.annotations")
        # Enrich last scored row
        if scored:
            scored[-1]["neighbour_beam_source"] = ann.get("neighbour_beam_source")
            scored[-1]["text"] = ann.get("text")
            scored[-1]["leaders"] = ann.get("leaders")
    for ch in (own.get("accepted_chains") or []) + (own.get("rejected_chains") or []):
        cid = ch.get("id") or ch.get("annotation_id") or ch.get("chain_id")
        if cid:
            _add(str(cid), "Chain", ch, "T18.chains")

    # T16 geometry scores (existing persisted confidence + reasons)
    t16_scores = []
    for e in t16_ents:
        t16_scores.append(
            {
                "entity_id": e.get("handle") or e.get("id"),
                "entity_type": e.get("type") or "DXFEntity",
                "source": "T16.beam_entity_ownership",
                "ownership": e.get("ownership"),
                "role": e.get("role"),
                "raw_score": e.get("confidence_score"),
                "normalised_score": e.get("confidence_score"),
                "total_ownership_score": e.get("confidence_score"),
                "reasons": e.get("reasons") or [],
                "layer": e.get("layer"),
                "note": (
                    "T16 additive confidence components are summarised in reasons[]; "
                    "full evidence dict is not persisted in by_beam."
                ),
            }
        )

    return {
        "beam_id": beam_id,
        "t18_scored_entities": scored,
        "t16_scored_entities": t16_scores,
        "t18_score_count": len(scored),
        "t16_score_count": len(t16_scores),
        "average_t18_score": _avg(
            [float(s["total_ownership_score"]) for s in scored if s.get("total_ownership_score") is not None]
        ),
        "average_accepted_score": _avg(
            [
                float(s["total_ownership_score"])
                for s in scored
                if s.get("accepted") and s.get("total_ownership_score") is not None
            ]
        ),
        "average_rejected_score": _avg(
            [
                float(s["total_ownership_score"] or 0.0)
                for s in scored
                if not s.get("accepted")
            ]
        ),
        "status": "PASS" if scored or t16_scores else "FAIL",
    }


def stage4_decision_traces(
    beam_id: str,
    own: Dict[str, Any],
    discovery: Dict[str, Any],
    scoring: Dict[str, Any],
    competitions: Dict[str, Any],
) -> Dict[str, Any]:
    traces: List[Dict[str, Any]] = []
    score_by_id = {
        s["entity_id"]: s for s in scoring.get("t18_scored_entities") or []
    }
    nearby_by_id = {
        e["entity_id"]: e for e in discovery.get("nearby_entities") or []
    }
    comps = competitions.get("by_entity") or {}

    # All considered entities
    for eid, s in score_by_id.items():
        near = nearby_by_id.get(eid) or {}
        comp = comps.get(eid) or {}
        steps = [
            {"step": "nearby", "result": near.get("inside_search_envelope", True)},
            {"step": "candidate", "result": True},
            {
                "step": "scored",
                "result": True,
                "total_ownership_score": s.get("total_ownership_score"),
                "score_breakdown": s.get("score_breakdown"),
            },
        ]
        if s.get("accepted_rules"):
            for r in s["accepted_rules"]:
                steps.append({"step": f"rule_pass:{r}", "result": True, "meaning": RULE_CATALOGUE.get(r, r)})
        if s.get("rejected_rule"):
            steps.append(
                {
                    "step": f"rule_reject:{s['rejected_rule']}",
                    "result": False,
                    "meaning": s.get("rejected_rule_meaning"),
                    "ownership_reason": s.get("ownership_reason"),
                    "neighbour_beam_source": s.get("neighbour_beam_source"),
                }
            )
        if comp.get("competing_beams"):
            steps.append(
                {
                    "step": "conflict_resolution",
                    "competing_beams": comp.get("competing_beams"),
                    "winning_beam": comp.get("winning_beam"),
                    "margin": comp.get("margin"),
                    "reason_winner_selected": comp.get("reason_winner_selected"),
                }
            )
        steps.append(
            {
                "step": "final_ownership",
                "owned_by": beam_id if s.get("accepted") else None,
                "accepted": s.get("accepted"),
                "ownership_reason": s.get("ownership_reason"),
            }
        )
        traces.append(
            {
                "entity_id": eid,
                "entity_type": s.get("entity_type"),
                "beam_id": beam_id,
                "decision_path": steps,
                "outcome": "OWNED" if s.get("accepted") else "REJECTED",
                "text": None,
            }
        )

    # Attach annotation text
    text_map = {}
    for ann in (own.get("accepted_annotations") or []) + (
        own.get("rejected_annotations") or []
    ):
        text_map[str(ann.get("id"))] = ann.get("text")
    for t in traces:
        if t["entity_id"] in text_map:
            t["text"] = text_map[t["entity_id"]]

    # Nearby but never considered
    for eid, near in nearby_by_id.items():
        if eid in score_by_id:
            continue
        if not near.get("inside_search_envelope"):
            continue
        traces.append(
            {
                "entity_id": eid,
                "entity_type": near.get("entity_type"),
                "beam_id": beam_id,
                "decision_path": [
                    {"step": "nearby", "result": True},
                    {
                        "step": "candidate",
                        "result": False,
                        "reason": near.get("reason_if_not_candidate")
                        or "Filtered before scoring",
                    },
                ],
                "outcome": "NOT_CANDIDATE",
                "text": None,
            }
        )

    return {
        "beam_id": beam_id,
        "traces": traces,
        "trace_count": len(traces),
        "owned_count": sum(1 for t in traces if t["outcome"] == "OWNED"),
        "rejected_count": sum(1 for t in traces if t["outcome"] == "REJECTED"),
        "not_candidate_count": sum(1 for t in traces if t["outcome"] == "NOT_CANDIDATE"),
        "status": "PASS" if traces else "FAIL",
    }


def stage5_coverage(
    beam_id: str,
    discovery: Dict[str, Any],
    scoring: Dict[str, Any],
    own: Dict[str, Any],
    competitions: Dict[str, Any],
) -> Dict[str, Any]:
    inside = sum(
        1
        for e in discovery.get("nearby_entities") or []
        if e.get("inside_search_envelope")
    )
    considered = int(discovery.get("candidate_count") or 0)
    scored = int(scoring.get("t18_score_count") or 0)
    owned = int((own.get("stats") or {}).get("accepted_annotation_count") or 0) + int(
        (own.get("stats") or {}).get("accepted_bar_count") or 0
    ) + int((own.get("stats") or {}).get("accepted_leader_count") or 0)
    rejected = int((own.get("stats") or {}).get("rejected_annotation_count") or 0) + int(
        (own.get("stats") or {}).get("rejected_bar_count") or 0
    )
    # leaders rejected inferred
    leader_rej = sum(
        1
        for r in (own.get("leader_results") or {}).values()
        if not (r or {}).get("accepted")
    )
    rejected += leader_rej

    owned_elsewhere = 0
    for eid, comp in (competitions.get("by_entity") or {}).items():
        if beam_id in (comp.get("considered_by") or []) and comp.get("winning_beam") not in (
            None,
            beam_id,
        ):
            # this beam considered but lost
            local = next(
                (
                    s
                    for s in scoring.get("t18_scored_entities") or []
                    if s["entity_id"] == eid and not s.get("accepted")
                ),
                None,
            )
            if local:
                owned_elsewhere += 1

    conflict_n = sum(
        1
        for c in (competitions.get("by_entity") or {}).values()
        if len(c.get("competing_beams") or []) >= 2
    ) + sum(
        1
        for c in (competitions.get("by_annotation_text") or {}).values()
        if len(c.get("considered_by") or []) >= 2
    )

    def pct(a: float, b: float) -> float:
        return round(100.0 * a / b, 2) if b else 0.0

    return {
        "beam_id": beam_id,
        "entities_inside_search_envelope": inside,
        "entities_considered": considered,
        "entities_scored": scored,
        "entities_owned": owned,
        "entities_rejected": rejected,
        "entities_owned_elsewhere": owned_elsewhere,
        "coverage_pct": pct(considered, max(inside, 1)),
        "scoring_pct": pct(scored, max(considered, 1)),
        "ownership_pct": pct(owned, max(scored, 1)),
        "conflict_pct": pct(conflict_n, max(scored, 1)),
        "stats_from_t18": own.get("stats") or {},
        "status": "PASS" if considered or scored else "FAIL",
    }


def stage6_failure_classification(
    beam_id: str,
    own: Dict[str, Any],
    discovery: Dict[str, Any],
    scoring: Dict[str, Any],
    coverage: Dict[str, Any],
    competitions: Dict[str, Any],
) -> Dict[str, Any]:
    """Exactly one primary cause for ownership shortfalls on this beam."""
    reasons = Counter()
    for ann in own.get("rejected_annotations") or []:
        reasons[ann.get("ownership_reason") or ann.get("rejected_rule") or "unknown"] += 1
    for ch in own.get("rejected_chains") or []:
        reasons[ch.get("ownership_reason") or ch.get("rejected_rule") or "unknown"] += 1
    for nid, res in (own.get("leader_results") or {}).items():
        if not (res or {}).get("accepted"):
            reasons[(res or {}).get("ownership_reason") or "leader_reject"] += 1
    for nid, res in (own.get("bar_results") or {}).items():
        if not (res or {}).get("accepted"):
            reasons[(res or {}).get("ownership_reason") or "bar_reject"] += 1

    rej_ann = int((own.get("stats") or {}).get("rejected_annotation_count") or 0)
    leakage = int((own.get("stats") or {}).get("cross_beam_leakage_count") or 0)
    not_cand = int(
        sum(
            1
            for e in discovery.get("nearby_entities") or []
            if e.get("inside_search_envelope") and not e.get("candidate")
        )
    )
    conflicts = sum(
        1
        for c in (competitions.get("by_entity") or {}).values()
        if len(c.get("competing_beams") or []) >= 2
    )

    # Primary cause selection
    primary = "Mixed"
    confidence = "Medium"
    detail = ""

    if not own:
        primary = "Candidate Discovery"
        confidence = "High"
        detail = "No BeamOwnership record for beam"
    elif rej_ann == 0 and leakage == 0 and not_cand == 0:
        primary = "Mixed"
        confidence = "Low"
        detail = "No clear ownership failures recorded; residual may be missing entities never discovered"
    elif any("neighbour" in str(r).lower() for r in reasons):
        primary = "Conflict Resolution"
        confidence = "High"
        detail = f"Neighbour/conflict reasons dominate: {reasons.most_common(3)}"
    elif any(
        "outside" in str(r).lower() or "envelope" in str(r).lower() for r in reasons
    ):
        primary = "Search Envelope"
        confidence = "High"
        detail = f"Envelope exclusion reasons: {reasons.most_common(3)}"
    elif any(
        "chain" in str(r).lower() or "leader" in str(r).lower() or "annotation" in str(r).lower()
        for r in reasons
    ):
        primary = "Annotation Dependency"
        confidence = "High"
        detail = f"Chain/annotation dependency: {reasons.most_common(3)}"
    elif not_cand > max(3, (discovery.get("candidate_count") or 0) // 2):
        primary = "Candidate Filtering"
        confidence = "Medium"
        detail = f"{not_cand} nearby entities never entered T18 scoring"
    elif conflicts >= 2:
        primary = "Conflict Resolution"
        confidence = "Medium"
        detail = f"{conflicts} multi-beam competitions"
    elif reasons:
        # Scoring-related rejects
        primary = "Ownership Scoring"
        confidence = "Medium"
        detail = f"Top reject reasons: {reasons.most_common(3)}"
    else:
        primary = "Candidate Discovery"
        confidence = "Medium"
        detail = "Failures without explicit rejection trail"

    return {
        "beam_id": beam_id,
        "primary_cause": primary,
        "confidence": confidence,
        "detail": detail,
        "rejection_reason_counts": dict(reasons),
        "rejected_annotation_count": rej_ann,
        "cross_beam_leakage_count": leakage,
        "nearby_not_candidate_count": not_cand,
        "multi_beam_conflict_count": conflicts,
        "status": "PASS",
    }


def _avg(vals: List[float]) -> float:
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def _t16_list(t16_beam: Any) -> List[Dict[str, Any]]:
    if not t16_beam:
        return []
    if isinstance(t16_beam, list):
        return t16_beam
    if isinstance(t16_beam, dict):
        for k in ("entities", "owned_entities", "items"):
            if isinstance(t16_beam.get(k), list):
                return t16_beam[k]
        # dict of handle -> entity
        vals = [v for v in t16_beam.values() if isinstance(v, dict) and ("ownership" in v or "handle" in v)]
        return vals
    return []


def explain_beam(
    beam_id: str,
    *,
    drawing_set: str,
    set_key: str,
    bundle: Dict[str, Any],
    graph_doc: Optional[Dict[str, Any]],
    competition_index: Dict[str, Any],
) -> Dict[str, Any]:
    own = _by_beam(bundle.get("beam_ownership"), beam_id)
    env_geom = _by_beam(bundle.get("geometry_envelopes"), beam_id)
    t16 = _t16_list(_by_beam(bundle.get("t16_ownership"), beam_id))
    merged = _by_beam(bundle.get("merged_ownership"), beam_id)
    own_diag = _by_beam(bundle.get("ownership_diagnostics"), beam_id)

    considered: Set[str] = set()
    considered.update(str(k) for k in (own.get("bar_results") or {}).keys())
    considered.update(str(k) for k in (own.get("leader_results") or {}).keys())
    for ann in (own.get("accepted_annotations") or []) + (
        own.get("rejected_annotations") or []
    ):
        if ann.get("id"):
            considered.add(str(ann["id"]))
    for nid in own.get("accepted_node_ids") or []:
        considered.add(str(nid))

    beam_nodes = _nodes_for_beam(graph_doc, beam_id)
    # Also include nodes referenced in ownership but not beam-tagged
    idx = _node_index(graph_doc)
    for nid in list(considered):
        if nid in idx and idx[nid] not in beam_nodes:
            beam_nodes.append(idx[nid])

    discovery = stage1_candidate_discovery(
        beam_id, own, env_geom, beam_nodes, considered
    )
    scoring = stage2_scoring(beam_id, own, t16)

    # Stage 3 slice for this beam from global competition index
    comps_for_beam = {
        "beam_id": beam_id,
        "by_entity": {
            eid: c
            for eid, c in (competition_index.get("by_entity") or {}).items()
            if beam_id in (c.get("considered_by") or [])
        },
        "by_annotation_text": {
            text: c
            for text, c in (competition_index.get("by_annotation_text") or {}).items()
            if beam_id in (c.get("considered_by") or [])
        },
    }
    comps_for_beam["competition_count"] = sum(
        1
        for c in comps_for_beam["by_entity"].values()
        if len(c.get("competing_beams") or []) >= 2
    ) + len(comps_for_beam["by_annotation_text"])

    traces = stage4_decision_traces(
        beam_id, own, discovery, scoring, comps_for_beam
    )
    coverage = stage5_coverage(beam_id, discovery, scoring, own, comps_for_beam)
    failure = stage6_failure_classification(
        beam_id, own, discovery, scoring, coverage, comps_for_beam
    )

    return {
        "beam_id": beam_id,
        "drawing_set": drawing_set,
        "set_key": set_key,
        "model_version": MODEL_VERSION,
        "has_ownership": bool(own),
        "artefacts": {
            "has_envelope": bool(own.get("envelope")),
            "has_t16": bool(t16),
            "has_merged": bool(merged),
            "has_diagnostics": bool(own_diag),
            "graph_node_count": len(beam_nodes),
        },
        "stage1_candidate_discovery": discovery,
        "stage2_ownership_scoring": scoring,
        "stage3_competing_beams": comps_for_beam,
        "stage4_decision_traces": traces,
        "stage5_coverage": coverage,
        "stage6_failure_classification": failure,
        "merged_ownership_counts": (merged or {}).get("counts"),
        "t18_stats": own.get("stats"),
    }
