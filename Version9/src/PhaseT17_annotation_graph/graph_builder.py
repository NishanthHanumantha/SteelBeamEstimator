"""
T1.7 deterministic Annotation Graph builder.
MODEL_VERSION: 9.4.0

Consumes R.1 / R.3.1 / T1.5 / T1.6 / R2.1B artefacts. Additive only.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence

from .graph_models import AnnotationGraph, make_edge, make_node
from .semantic_classifier import classify_annotation_text

MODEL_VERSION = "9.4.0"
PHASE_ID = "T1.7"

# Engineering tolerances (mm)
ANN_LEADER_TAIL_TOL = 300.0
LEADER_BAR_TIP_TOL = 80.0
LEADER_BAR_TIP_MED = 150.0
ANN_BAR_PROX_TOL = 400.0
SUPPORT_TIP_TOL = 250.0


def _dist(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)


def _point_to_segment(
    px: float, py: float, x0: float, y0: float, x1: float, y1: float
) -> float:
    dx, dy = x1 - x0, y1 - y0
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return _dist(px, py, x0, y0)
    t = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / (dx * dx + dy * dy)))
    return _dist(px, py, x0 + t * dx, y0 + t * dy)


def _conf_from_dist(d: float, high: float, med: float) -> str:
    if d <= high:
        return "HIGH"
    if d <= med:
        return "MEDIUM"
    return "LOW"


def build_annotation_graph(
    *,
    beam_ids: Sequence[str],
    envelopes: Dict[str, Dict[str, Any]],
    annotations_by_beam: Dict[str, List[Dict[str, Any]]],
    leaders: List[Dict[str, Any]],
    physical_bars: List[Dict[str, Any]],
    ownership_by_beam: Dict[str, List[Dict[str, Any]]],
    r31_relationships: Optional[List[Dict[str, Any]]] = None,
    eso_by_ann: Optional[Dict[str, Dict[str, Any]]] = None,
    arrow_inventory: Optional[List[Dict[str, Any]]] = None,
    supports_by_beam: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    inventory_by_handle: Optional[Dict[str, Dict[str, Any]]] = None,
) -> AnnotationGraph:
    """Build the full AnnotationGraph for the requested beams."""
    g = AnnotationGraph()
    g.meta = {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "inputs": [
            "reinforcement_annotations.json",
            "PhysicalBars.json",
            "LeaderInventory.json",
            "geometry_envelopes.json",
            "beam_entity_ownership.json",
            "EngineeringDrawingRelationships.json",
            "engineering_semantic_objects.json",
        ],
        "policy": "deterministic_engineering_rules_only",
    }
    eso_by_ann = eso_by_ann or {}
    r31_relationships = r31_relationships or []
    arrow_inventory = arrow_inventory or []
    supports_by_beam = supports_by_beam or {}
    inventory_by_handle = inventory_by_handle or {}

    edge_seq = 0

    def _eid(prefix: str = "E") -> str:
        nonlocal edge_seq
        edge_seq += 1
        return f"{prefix}::{edge_seq:06d}"

    def _link(
        etype: str,
        src: str,
        tgt: str,
        beam_id: str,
        confidence: str,
        reason: str,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> None:
        g.add_edge(
            make_edge(
                _eid(),
                etype,
                src,
                tgt,
                beam_id=beam_id,
                confidence=confidence,
                reason=reason,
                evidence=evidence,
            )
        )

    # Index helpers
    leaders_by_beam: Dict[str, List[Dict[str, Any]]] = {}
    for L in leaders:
        bid = str(L.get("beam_id") or "")
        if bid:
            leaders_by_beam.setdefault(bid, []).append(L)

    bars_by_beam: Dict[str, List[Dict[str, Any]]] = {}
    for b in physical_bars:
        bid = str(b.get("beam_id") or "")
        if bid:
            bars_by_beam.setdefault(bid, []).append(b)

    r31_by_ann = {
        str(r["annotation_id"]): r
        for r in r31_relationships
        if r.get("annotation_id")
    }
    arrows_by_leader = {
        str(a.get("leader_id")): a
        for a in arrow_inventory
        if a.get("leader_id")
    }

    for beam_id in beam_ids:
        env = envelopes.get(beam_id) or {}
        if not env and beam_id not in annotations_by_beam:
            continue

        # ---- Beam node ----
        axis = env.get("axis") or {}
        beam_node_id = f"BEAM::{beam_id}"
        g.add_node(
            make_node(
                beam_node_id,
                "Beam",
                beam_id,
                source="T1.5+registry",
                confidence=str(env.get("geometry_confidence") or "HIGH"),
                attributes={
                    "extent": env.get("extent"),
                    "axis": axis,
                    "depth_mm": env.get("depth_mm"),
                    "span_mm": (env.get("meta") or {}).get("span_mm"),
                    "signals_used": env.get("signals_used"),
                },
            )
        )

        # ---- Supports ----
        for i, S in enumerate(supports_by_beam.get(beam_id) or []):
            sid = str(S.get("support_id") or f"SUP::{beam_id}::{i}")
            g.add_node(
                make_node(
                    sid,
                    "Support",
                    beam_id,
                    source="R.3/supports",
                    confidence=str(S.get("confidence") or "MEDIUM"),
                    attributes=dict(S),
                )
            )
            _link("OWNS", beam_node_id, sid, beam_id, "HIGH", "beam_owns_support")
            _link(
                "ANCHORS",
                sid,
                beam_node_id,
                beam_id,
                "MEDIUM",
                "support_anchors_beam",
            )

        # ---- Owned entities (T1.6) — LINE bars used when PhysicalBars sparse ----
        owned_rows = ownership_by_beam.get(beam_id) or []
        owned_bar_lines: List[Dict[str, Any]] = []
        for row in owned_rows:
            h = str(row.get("handle") or "").upper()
            if not h:
                continue
            oid = f"OWN::{beam_id}::{h}"
            g.add_node(
                make_node(
                    oid,
                    "OwnedEntity",
                    beam_id,
                    source="T1.6",
                    confidence=str(row.get("ownership") or "UNKNOWN"),
                    attributes={
                        "handle": h,
                        "entity_type": row.get("type"),
                        "ownership": row.get("ownership"),
                        "role": row.get("role"),
                        "layer": row.get("layer"),
                        "reasons": row.get("reasons"),
                        "confidence_score": row.get("confidence_score"),
                    },
                )
            )
            if row.get("ownership") == "HIGH":
                _link(
                    "OWNS",
                    beam_node_id,
                    oid,
                    beam_id,
                    "HIGH",
                    "t16_high_ownership",
                )
            if (
                row.get("ownership") == "HIGH"
                and row.get("type") in ("LINE", "LWPOLYLINE")
                and str(row.get("role") or "")
                in (
                    "TOP_BAR",
                    "BOTTOM_BAR",
                    "LONGITUDINAL_BAR",
                    "STIRRUP_GEOMETRY",
                    "STIRRUP_OR_SUPPORT",
                )
            ):
                inv = inventory_by_handle.get(h) or {}
                owned_bar_lines.append(
                    {
                        "handle": h,
                        "role": row.get("role"),
                        "owned_node_id": oid,
                        "start_point": inv.get("start_point"),
                        "end_point": inv.get("end_point"),
                        "y": (inv.get("centroid") or [None, None])[1]
                        if inv.get("centroid")
                        else None,
                    }
                )

        # ---- Physical bars (R3.1) + synthetic from T1.6 when missing ----
        bar_nodes: List[Dict[str, Any]] = []
        r31_bars = bars_by_beam.get(beam_id) or []
        for b in r31_bars:
            bid = str(b.get("bar_id"))
            g.add_node(
                make_node(
                    bid,
                    "PhysicalBar",
                    beam_id,
                    source="R.3.1",
                    confidence=str(b.get("bar_confidence") or "MEDIUM"),
                    attributes=dict(b),
                )
            )
            _link(
                "OWNS",
                beam_node_id,
                bid,
                beam_id,
                "HIGH",
                "r31_physical_bar",
            )
            bar_nodes.append({"id": bid, "attrs": b, "source": "R.3.1"})

        if not r31_bars and owned_bar_lines:
            # Synthesize PhysicalBar nodes from HIGH-owned longitudinal lines
            for i, line in enumerate(owned_bar_lines):
                if line.get("role") not in (
                    "TOP_BAR",
                    "BOTTOM_BAR",
                    "LONGITUDINAL_BAR",
                ):
                    continue
                sp, ep = line.get("start_point"), line.get("end_point")
                if not sp or not ep:
                    continue
                syn_id = f"BAR::SYN::{beam_id}::{line['handle']}"
                place = "TOP_FACE" if "TOP" in str(line.get("role")) else (
                    "BOTTOM_FACE" if "BOTTOM" in str(line.get("role")) else "UNKNOWN"
                )
                attrs = {
                    "bar_id": syn_id,
                    "beam_id": beam_id,
                    "entity_type": "LINE",
                    "start_x": sp[0],
                    "end_x": ep[0],
                    "y_position": 0.5 * (sp[1] + ep[1]),
                    "bar_length_mm": abs(ep[0] - sp[0]),
                    "vertical_placement": place,
                    "bar_confidence": "MEDIUM",
                    "dxf_handle": line["handle"],
                    "synthetic": True,
                    "synthetic_reason": "r31_empty_used_t16_owned_line",
                }
                g.add_node(
                    make_node(
                        syn_id,
                        "PhysicalBar",
                        beam_id,
                        source="T1.6_synthetic",
                        confidence="MEDIUM",
                        attributes=attrs,
                    )
                )
                _link(
                    "OWNS",
                    beam_node_id,
                    syn_id,
                    beam_id,
                    "MEDIUM",
                    "synthetic_bar_from_t16",
                )
                _link(
                    "MATCHES_ENTITY",
                    syn_id,
                    line["owned_node_id"],
                    beam_id,
                    "HIGH",
                    "bar_matches_owned_line",
                    {"handle": line["handle"]},
                )
                bar_nodes.append({"id": syn_id, "attrs": attrs, "source": "synthetic"})

        # Match R3.1 bars to owned LINE handles when possible
        for bn in bar_nodes:
            if bn["source"] != "R.3.1":
                continue
            attrs = bn["attrs"]
            try:
                y = float(attrs["y_position"])
                x0, x1 = float(attrs["start_x"]), float(attrs["end_x"])
            except Exception:
                continue
            best = None
            best_d = 1e18
            for line in owned_bar_lines:
                sp, ep = line.get("start_point"), line.get("end_point")
                if not sp or not ep:
                    continue
                d = _point_to_segment(
                    0.5 * (x0 + x1), y, sp[0], sp[1], ep[0], ep[1]
                )
                if d < best_d:
                    best_d = d
                    best = line
            if best and best_d <= LEADER_BAR_TIP_TOL:
                _link(
                    "MATCHES_ENTITY",
                    bn["id"],
                    best["owned_node_id"],
                    beam_id,
                    _conf_from_dist(best_d, 20, 50),
                    f"bar_to_owned_line_dist={best_d:.1f}mm",
                    {"distance_mm": round(best_d, 2), "handle": best["handle"]},
                )

        # ---- Leaders + arrows ----
        leader_nodes: List[Dict[str, Any]] = []
        for L in leaders_by_beam.get(beam_id) or []:
            lid = str(L.get("leader_id"))
            g.add_node(
                make_node(
                    lid,
                    "Leader",
                    beam_id,
                    source="R.3.1",
                    confidence="HIGH",
                    attributes=dict(L),
                )
            )
            _link("OWNS", beam_node_id, lid, beam_id, "HIGH", "r31_leader_beam_id")
            leader_nodes.append(L)

            # Arrow node
            arr = arrows_by_leader.get(lid)
            aid = str((arr or {}).get("arrow_id") or f"ARR::{lid}")
            g.add_node(
                make_node(
                    aid,
                    "LeaderArrow",
                    beam_id,
                    source="R.3.1" if arr else "derived",
                    confidence="HIGH" if arr else "MEDIUM",
                    attributes=arr or {
                        "arrow_id": aid,
                        "leader_id": lid,
                        "tip_x": L.get("tip_x"),
                        "tip_y": L.get("tip_y"),
                    },
                )
            )
            _link("HAS_ARROW", lid, aid, beam_id, "HIGH", "leader_has_arrow")

            # LeaderTarget at tip
            tid = f"LTGT::{lid}"
            g.add_node(
                make_node(
                    tid,
                    "LeaderTarget",
                    beam_id,
                    source="derived",
                    confidence="HIGH",
                    attributes={
                        "x": L.get("tip_x"),
                        "y": L.get("tip_y"),
                        "leader_id": lid,
                    },
                )
            )
            _link("TARGETS", lid, tid, beam_id, "HIGH", "leader_tip_target")
            _link("POINTS_TO", aid, tid, beam_id, "HIGH", "arrow_points_to_target")

            # Leader tip → PhysicalBar
            try:
                tip_x, tip_y = float(L["tip_x"]), float(L["tip_y"])
            except Exception:
                continue
            best_bar = None
            best_d = 1e18
            for bn in bar_nodes:
                a = bn["attrs"]
                try:
                    y = float(a["y_position"])
                    x0, x1 = float(a["start_x"]), float(a["end_x"])
                except Exception:
                    continue
                d = _point_to_segment(tip_x, tip_y, x0, y, x1, y)
                if d < best_d:
                    best_d = d
                    best_bar = bn
            # Also try owned lines directly
            best_line = None
            best_line_d = 1e18
            for line in owned_bar_lines:
                sp, ep = line.get("start_point"), line.get("end_point")
                if not sp or not ep:
                    continue
                d = _point_to_segment(tip_x, tip_y, sp[0], sp[1], ep[0], ep[1])
                if d < best_line_d:
                    best_line_d = d
                    best_line = line

            if best_bar and best_d <= LEADER_BAR_TIP_MED:
                conf = _conf_from_dist(best_d, LEADER_BAR_TIP_TOL, LEADER_BAR_TIP_MED)
                _link(
                    "POINTS_TO",
                    lid,
                    best_bar["id"],
                    beam_id,
                    conf,
                    f"leader_tip_to_bar_dist={best_d:.1f}mm",
                    {"distance_mm": round(best_d, 2)},
                )
                _link(
                    "POINTS_TO",
                    aid,
                    best_bar["id"],
                    beam_id,
                    conf,
                    f"arrow_tip_to_bar_dist={best_d:.1f}mm",
                    {"distance_mm": round(best_d, 2)},
                )
                _link(
                    "PROPAGATES_TO",
                    lid,
                    beam_node_id,
                    beam_id,
                    conf,
                    "leader_to_bar_to_beam",
                )
            elif best_line and best_line_d <= LEADER_BAR_TIP_MED:
                conf = _conf_from_dist(
                    best_line_d, LEADER_BAR_TIP_TOL, LEADER_BAR_TIP_MED
                )
                _link(
                    "POINTS_TO",
                    lid,
                    best_line["owned_node_id"],
                    beam_id,
                    conf,
                    f"leader_tip_to_owned_line_dist={best_line_d:.1f}mm",
                    {"distance_mm": round(best_line_d, 2), "handle": best_line["handle"]},
                )
                _link(
                    "PROPAGATES_TO",
                    lid,
                    beam_node_id,
                    beam_id,
                    conf,
                    "leader_to_owned_line_to_beam",
                )

            # Leader tip near support
            for S in supports_by_beam.get(beam_id) or []:
                try:
                    sx = float(S.get("x") or S.get("support_x") or S.get("dxf_x"))
                    sy = float(S.get("y") or S.get("support_y") or axis.get("mark_y") or tip_y)
                except Exception:
                    continue
                d = _dist(tip_x, tip_y, sx, sy)
                if d <= SUPPORT_TIP_TOL:
                    sid = str(S.get("support_id") or "")
                    if sid and sid in g.nodes:
                        _link(
                            "NEAR",
                            lid,
                            sid,
                            beam_id,
                            _conf_from_dist(d, 80, SUPPORT_TIP_TOL),
                            f"leader_tip_near_support_dist={d:.1f}mm",
                            {"distance_mm": round(d, 2)},
                        )

        # ---- Annotations + semantics ----
        anns = annotations_by_beam.get(beam_id) or []
        for a in anns:
            ann_id = str(a.get("annotation_id"))
            text = str(a.get("clean_text") or "")
            eso = eso_by_ann.get(ann_id)
            sem = classify_annotation_text(
                text, r1_role=a.get("role"), eso=eso
            )
            # Primary annotation node
            g.add_node(
                make_node(
                    ann_id,
                    "Annotation",
                    beam_id,
                    source="R.1",
                    confidence=str(a.get("confidence") or a.get("association_confidence") or "MEDIUM"),
                    attributes={
                        "clean_text": text,
                        "x": a.get("x"),
                        "y": a.get("y"),
                        "r1_role": a.get("role"),
                        "quantity": a.get("quantity"),
                        "diameter_mm": a.get("diameter_mm"),
                        "spacing_mm": a.get("spacing_mm"),
                        "position_zone": a.get("position_zone"),
                        "association_method": a.get("association_method"),
                    },
                )
            )
            _link(
                "OWNS",
                beam_node_id,
                ann_id,
                beam_id,
                "HIGH",
                "r1_beam_association",
            )

            # Semantic node
            sem_id = f"SEM::{ann_id}"
            g.add_node(
                make_node(
                    sem_id,
                    sem["node_type"],
                    beam_id,
                    source="T1.7_semantic_classifier"
                    + ("+ESO" if eso else ""),
                    confidence="HIGH"
                    if sem["semantic_type"]
                    not in ("Unknown", "DimensionNote")
                    else "LOW",
                    attributes={
                        **sem,
                        "eso_engineering_role": (eso or {}).get("engineering_role"),
                        "eso_placement": (eso or {}).get("placement"),
                    },
                )
            )
            _link(
                "INTERPRETS",
                sem_id,
                ann_id,
                beam_id,
                "HIGH"
                if sem["semantic_type"] != "Unknown"
                else "LOW",
                "semantic_interprets_annotation",
                {"semantic_type": sem["semantic_type"], "reasons": sem["reasons"]},
            )

            # Attach annotation ↔ leader
            linked_leader = None
            r31 = r31_by_ann.get(ann_id) or {}
            if r31.get("leader_id"):
                linked_leader = str(r31["leader_id"])
                conf = str(r31.get("relationship_confidence") or "MEDIUM")
                if linked_leader in g.nodes:
                    _link(
                        "ATTACHED_TO",
                        ann_id,
                        linked_leader,
                        beam_id,
                        conf,
                        "r31_annotation_leader",
                        {
                            "relationship_id": r31.get("relationship_id"),
                            "relationship_reason": r31.get("relationship_reason"),
                        },
                    )
                    _link(
                        "DESCRIBES",
                        ann_id,
                        linked_leader,
                        beam_id,
                        conf,
                        "annotation_describes_via_leader",
                    )
                    # Propagate: annotation → leader → bar → beam already; also direct DESCRIBES bar
                    for e in list(g.edges):
                        if (
                            e["source_id"] == linked_leader
                            and e["type"] == "POINTS_TO"
                            and g.nodes.get(e["target_id"], {}).get("type")
                            in ("PhysicalBar", "OwnedEntity")
                        ):
                            _link(
                                "DESCRIBES",
                                ann_id,
                                e["target_id"],
                                beam_id,
                                conf,
                                "annotation_describes_bar_via_leader_chain",
                            )

            # Geometric fallback: nearest leader tail (wider for Ld / stirrup)
            if not linked_leader:
                try:
                    ax, ay = float(a["x"]), float(a["y"])
                except Exception:
                    ax = ay = None
                if ax is not None:
                    tol = ANN_LEADER_TAIL_TOL
                    if sem["semantic_type"] in (
                        "DevelopmentLength",
                        "StirrupNote",
                        "SideFaceReinforcement",
                    ):
                        tol = 550.0
                    best_L = None
                    best_d = 1e18
                    best_mode = "tail"
                    for L in leader_nodes:
                        try:
                            d_tail = _dist(
                                ax, ay, float(L["tail_x"]), float(L["tail_y"])
                            )
                            # Also consider mid-shoulder / tip for short leaders
                            d_tip = _dist(
                                ax, ay, float(L["tip_x"]), float(L["tip_y"])
                            )
                        except Exception:
                            continue
                        d = d_tail
                        mode = "tail"
                        if d_tip < d and sem["semantic_type"] == "DevelopmentLength":
                            # Ld notes often sit near the tip/arrow of the Ld callout
                            d = d_tip
                            mode = "tip"
                        if d < best_d:
                            best_d = d
                            best_L = L
                            best_mode = mode
                    if best_L and best_d <= tol:
                        lid = str(best_L["leader_id"])
                        conf = _conf_from_dist(best_d, 120, tol)
                        _link(
                            "ATTACHED_TO",
                            ann_id,
                            lid,
                            beam_id,
                            conf,
                            f"ann_to_leader_{best_mode}_dist={best_d:.1f}mm",
                            {"distance_mm": round(best_d, 2), "mode": best_mode},
                        )
                        linked_leader = lid
                        for e in list(g.edges):
                            if (
                                e["source_id"] == lid
                                and e["type"] == "POINTS_TO"
                                and g.nodes.get(e["target_id"], {}).get("type")
                                in ("PhysicalBar", "OwnedEntity")
                            ):
                                _link(
                                    "DESCRIBES",
                                    ann_id,
                                    e["target_id"],
                                    beam_id,
                                    conf,
                                    "annotation_describes_bar_via_geom_leader",
                                )
                    elif sem["semantic_type"] == "DevelopmentLength":
                        # Ld always belongs to the beam even without a leader
                        _link(
                            "PROPAGATES_TO",
                            ann_id,
                            beam_node_id,
                            beam_id,
                            "MEDIUM",
                            "ld_annotation_belongs_to_beam",
                        )
                    elif sem["semantic_type"] == "StirrupNote":
                        _link(
                            "PROPAGATES_TO",
                            ann_id,
                            beam_node_id,
                            beam_id,
                            "MEDIUM",
                            "stirrup_annotation_belongs_to_beam",
                        )

            # Annotation near bar without leader (side-face / Ld often)
            if sem["semantic_type"] in (
                "SideFaceReinforcement",
                "DevelopmentLength",
                "BarCallout",
                "StirrupNote",
            ):
                try:
                    ax, ay = float(a["x"]), float(a["y"])
                except Exception:
                    ax = ay = None
                if ax is not None and bar_nodes:
                    best_bar = None
                    best_d = 1e18
                    for bn in bar_nodes:
                        aa = bn["attrs"]
                        try:
                            y = float(aa["y_position"])
                            x0, x1 = float(aa["start_x"]), float(aa["end_x"])
                            mx = min(max(ax, min(x0, x1)), max(x0, x1))
                            d = _dist(ax, ay, mx, y)
                        except Exception:
                            continue
                        if d < best_d:
                            best_d = d
                            best_bar = bn
                    if best_bar and best_d <= ANN_BAR_PROX_TOL:
                        # Only add if no DESCRIBES yet
                        already = any(
                            e["source_id"] == ann_id
                            and e["type"] == "DESCRIBES"
                            and e["target_id"] == best_bar["id"]
                            for e in g.edges
                        )
                        if not already:
                            _link(
                                "DESCRIBES",
                                ann_id,
                                best_bar["id"],
                                beam_id,
                                _conf_from_dist(best_d, 150, ANN_BAR_PROX_TOL),
                                f"ann_proximity_to_bar={best_d:.1f}mm",
                                {
                                    "distance_mm": round(best_d, 2),
                                    "semantic_type": sem["semantic_type"],
                                },
                            )

            # Match annotation text entity from T1.6 HIGH TEXT/MTEXT
            try:
                ax, ay = float(a["x"]), float(a["y"])
            except Exception:
                ax = ay = None
            if ax is not None:
                for row in owned_rows:
                    if row.get("type") not in ("TEXT", "MTEXT", "ATTRIB"):
                        continue
                    if row.get("ownership") != "HIGH":
                        continue
                    h = str(row.get("handle") or "").upper()
                    inv = inventory_by_handle.get(h) or {}
                    sp = inv.get("start_point") or inv.get("centroid")
                    if not sp:
                        continue
                    d = _dist(ax, ay, float(sp[0]), float(sp[1]))
                    txt = (inv.get("text") or "").replace("%%U", "")
                    text_hit = bool(text) and (
                        text[:12].upper() in txt.upper() or txt[:12].upper() in text.upper()
                    )
                    if d <= 120 or text_hit and d <= 400:
                        oid = f"OWN::{beam_id}::{h}"
                        if oid in g.nodes:
                            _link(
                                "MATCHES_ENTITY",
                                ann_id,
                                oid,
                                beam_id,
                                "HIGH" if d <= 120 else "MEDIUM",
                                f"ann_matches_owned_text_dist={d:.1f}mm",
                                {"distance_mm": round(d, 2), "handle": h},
                            )

        # ---- Dimensions from ownership ----
        for row in owned_rows:
            if row.get("type") != "DIMENSION" or row.get("ownership") != "HIGH":
                continue
            h = str(row.get("handle") or "").upper()
            did = f"DIM::{beam_id}::{h}"
            g.add_node(
                make_node(
                    did,
                    "Dimension",
                    beam_id,
                    source="T1.6",
                    confidence="HIGH",
                    attributes={
                        "handle": h,
                        "role": row.get("role"),
                        "layer": row.get("layer"),
                    },
                )
            )
            _link("OWNS", beam_node_id, did, beam_id, "HIGH", "owned_dimension")
            # MEASURES nearest bar
            inv = inventory_by_handle.get(h) or {}
            cent = inv.get("centroid") or inv.get("start_point")
            if cent and bar_nodes:
                best_bar = None
                best_d = 1e18
                for bn in bar_nodes:
                    aa = bn["attrs"]
                    try:
                        y = float(aa["y_position"])
                        d = abs(float(cent[1]) - y)
                    except Exception:
                        continue
                    if d < best_d:
                        best_d = d
                        best_bar = bn
                if best_bar and best_d <= 500:
                    _link(
                        "MEASURES",
                        did,
                        best_bar["id"],
                        beam_id,
                        _conf_from_dist(best_d, 100, 300),
                        f"dimension_near_bar_dy={best_d:.1f}mm",
                        {"dy_mm": round(best_d, 2)},
                    )

    g.finalize()
    return g
