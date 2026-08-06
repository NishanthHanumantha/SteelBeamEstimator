"""
T1.8 — Filter AnnotationGraph chains through Beam Ownership Envelope.
MODEL_VERSION: 9.5.0
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from .beam_envelope import build_beam_envelope
from .ownership_rules import (
    evaluate_annotation_chain,
    evaluate_leader,
    evaluate_physical_bar,
    evaluate_semantic,
)

MODEL_VERSION = "9.5.0"


def _index_graph(graph: Dict[str, Any], beam_id: str):
    nodes = {
        n["id"]: n
        for n in (graph.get("nodes") or [])
        if n.get("beam_id") == beam_id
    }
    edges = [e for e in (graph.get("edges") or []) if e.get("beam_id") == beam_id]
    out: Dict[str, List[Dict[str, Any]]] = {}
    for e in edges:
        out.setdefault(e["source_id"], []).append(e)
    return nodes, edges, out


def filter_beam_ownership(
    beam_id: str,
    graph: Dict[str, Any],
    geometry_envelope: Dict[str, Any],
    r31_bars: List[Dict[str, Any]],
    r1_annotations: List[Dict[str, Any]],
    *,
    inventory_bar_ys: Optional[List[float]] = None,
    inventory_by_handle: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    nodes, edges, out_edges = _index_graph(graph, beam_id)
    inventory_by_handle = inventory_by_handle or {}

    # Bars from graph PhysicalBar nodes (includes T1.7 synthetics)
    graph_bars = [
        {
            "bar_id": n["id"],
            "start_x": (n.get("attributes") or {}).get("start_x"),
            "end_x": (n.get("attributes") or {}).get("end_x"),
            "y_position": (n.get("attributes") or {}).get("y_position"),
            "vertical_placement": (n.get("attributes") or {}).get("vertical_placement"),
        }
        for n in nodes.values()
        if n.get("type") == "PhysicalBar"
    ]
    # Also lift T1.6 HIGH longitudinal OwnedEntities into envelope construction
    owned_geom_bars: List[Dict[str, Any]] = []
    for n in nodes.values():
        if n.get("type") != "OwnedEntity":
            continue
        attrs = n.get("attributes") or {}
        if attrs.get("ownership") != "HIGH":
            continue
        if str(attrs.get("role") or "") not in (
            "TOP_BAR",
            "BOTTOM_BAR",
            "LONGITUDINAL_BAR",
        ):
            continue
        h = str(attrs.get("handle") or "").upper()
        ent = inventory_by_handle.get(h) or {}
        sp, ep = ent.get("start_point"), ent.get("end_point")
        if not sp or not ep:
            continue
        owned_geom_bars.append(
            {
                "bar_id": n["id"],
                "start_x": sp[0],
                "end_x": ep[0],
                "y_position": 0.5 * (float(sp[1]) + float(ep[1])),
                "vertical_placement": "TOP_FACE"
                if "TOP" in str(attrs.get("role"))
                else "BOTTOM_FACE",
            }
        )

    all_bars = list(r31_bars) + graph_bars + owned_geom_bars

    envelope = build_beam_envelope(
        beam_id,
        geometry_envelope,
        all_bars,
        r1_annotations,
        inventory_bar_ys=inventory_bar_ys,
    )

    bar_results: Dict[str, Dict[str, Any]] = {}
    for n in nodes.values():
        if n.get("type") != "PhysicalBar":
            continue
        bar_results[n["id"]] = evaluate_physical_bar(n, envelope)

    # OwnedEntity longitudinal lines: evaluate directly against envelope
    owned_as_bar: Dict[str, Dict[str, Any]] = {}
    for n in nodes.values():
        if n.get("type") != "OwnedEntity":
            continue
        attrs = n.get("attributes") or {}
        h = str(attrs.get("handle") or "").upper()
        ent = inventory_by_handle.get(h) or {}
        sp, ep = ent.get("start_point"), ent.get("end_point")
        role = str(attrs.get("role") or "")
        is_bar_role = role in (
            "TOP_BAR",
            "BOTTOM_BAR",
            "LONGITUDINAL_BAR",
            "STIRRUP_GEOMETRY",
        )
        if (
            attrs.get("ownership") == "HIGH"
            and is_bar_role
            and sp
            and ep
            and abs(float(ep[1]) - float(sp[1])) < 80
        ):
            pseudo = {
                "attributes": {
                    "start_x": float(sp[0]),
                    "end_x": float(ep[0]),
                    "y_position": 0.5 * (float(sp[1]) + float(ep[1])),
                }
            }
            owned_as_bar[n["id"]] = evaluate_physical_bar(pseudo, envelope)
            if owned_as_bar[n["id"]].get("accepted"):
                owned_as_bar[n["id"]]["ownership_reason"] = (
                    "owned_longitudinal_line_in_envelope"
                )
        else:
            owned_as_bar[n["id"]] = {
                "accepted": False,
                "accepted_rules": [],
                "rejected_rule": "R1_PHYSICAL_BAR",
                "ownership_reason": "owned_entity_not_longitudinal_or_no_geom",
                "ownership_score": 0.0,
            }

    for e in edges:
        if e.get("type") != "MATCHES_ENTITY":
            continue
        if e["source_id"] in bar_results and bar_results[e["source_id"]].get("accepted"):
            if e["target_id"] in owned_as_bar and not owned_as_bar[e["target_id"]].get(
                "accepted"
            ):
                owned_as_bar[e["target_id"]] = {
                    "accepted": True,
                    "accepted_rules": ["R1_PHYSICAL_BAR"],
                    "rejected_rule": None,
                    "ownership_reason": "matches_accepted_physical_bar",
                    "ownership_score": 0.7,
                }

    def _target_bar_result(target_id: str) -> Optional[Dict[str, Any]]:
        if target_id in bar_results:
            return bar_results[target_id]
        if target_id in owned_as_bar:
            return owned_as_bar[target_id]
        return None

    leader_results: Dict[str, Dict[str, Any]] = {}
    for n in nodes.values():
        if n.get("type") != "Leader":
            continue
        pointed = None
        for e in out_edges.get(n["id"], []):
            if e.get("type") != "POINTS_TO":
                continue
            br = _target_bar_result(e["target_id"])
            if br is not None:
                pointed = br
                if br.get("accepted"):
                    break
        leader_results[n["id"]] = evaluate_leader(n, envelope, pointed)

    # Map annotation → semantic
    sem_for_ann: Dict[str, Dict[str, Any]] = {}
    for n in nodes.values():
        if n.get("type") not in (
            "SemanticFact",
            "DevelopmentLength",
            "SideFaceReinforcement",
            "StirrupNote",
            "SpacerBar",
        ):
            continue
        for e in out_edges.get(n["id"], []):
            if e.get("type") == "INTERPRETS":
                sem_for_ann[e["target_id"]] = n

    ann_results: Dict[str, Dict[str, Any]] = {}
    chains_accepted: List[Dict[str, Any]] = []
    chains_rejected: List[Dict[str, Any]] = []

    for n in nodes.values():
        if n.get("type") != "Annotation":
            continue
        # Find leaders / described bars
        leaders = []
        describes_bars = []
        for e in out_edges.get(n["id"], []):
            if e.get("type") == "ATTACHED_TO" and e["target_id"] in leader_results:
                leaders.append(e["target_id"])
            if e.get("type") == "DESCRIBES":
                describes_bars.append(e["target_id"])

        best_leader_res = None
        best_bar_res = None
        for lid in leaders:
            lr = leader_results[lid]
            if best_leader_res is None or (
                lr.get("accepted") and not best_leader_res.get("accepted")
            ):
                best_leader_res = lr
            for e in out_edges.get(lid, []):
                if e.get("type") != "POINTS_TO":
                    continue
                br = _target_bar_result(e["target_id"])
                if br and br.get("accepted"):
                    best_bar_res = br
                    best_leader_res = lr
                    break

        describes_owned = any(
            (_target_bar_result(bid) or {}).get("accepted") for bid in describes_bars
        )
        # Also: DESCRIBES → OwnedEntity that matches accepted bar
        if not describes_owned:
            for bid in describes_bars:
                if (owned_as_bar.get(bid) or {}).get("accepted"):
                    describes_owned = True
                    break
                # Direct PhysicalBar
                if (bar_results.get(bid) or {}).get("accepted"):
                    describes_owned = True
                    break

        sem = sem_for_ann.get(n["id"])
        res = evaluate_annotation_chain(
            n,
            envelope,
            leader_result=best_leader_res,
            bar_result=best_bar_res,
            describes_owned_bar=describes_owned,
            sem_node=sem,
        )
        ann_results[n["id"]] = res

        chain = {
            "annotation_id": n["id"],
            "text": (n.get("attributes") or {}).get("clean_text"),
            "leaders": leaders,
            "describes": describes_bars,
            "semantic_id": sem["id"] if sem else None,
            "semantic_type": (sem.get("attributes") or {}).get("semantic_type")
            if sem
            else None,
            **res,
        }
        if res.get("accepted"):
            chains_accepted.append(chain)
        else:
            # Guess neighbour beam when on wrong side of mark
            mark_y = envelope["centreline"]["y"]
            ay = float((n.get("attributes") or {}).get("y") or mark_y)
            neighbour_hint = None
            if envelope["side_of_mark"] == "ABOVE_MARK" and ay < mark_y:
                neighbour_hint = "BELOW_MARK_NEIGHBOUR"
            elif envelope["side_of_mark"] == "BELOW_MARK" and ay > mark_y:
                neighbour_hint = "ABOVE_MARK_NEIGHBOUR"
            chain["neighbour_beam_source"] = neighbour_hint
            chains_rejected.append(chain)

    sem_results: Dict[str, Dict[str, Any]] = {}
    for ann_id, sem in sem_for_ann.items():
        sem_results[sem["id"]] = evaluate_semantic(sem, ann_results.get(ann_id))

    accepted_node_ids: Set[str] = set()
    # Beam node always
    for n in nodes.values():
        if n.get("type") == "Beam":
            accepted_node_ids.add(n["id"])

    for bid, res in bar_results.items():
        if res.get("accepted"):
            accepted_node_ids.add(bid)
    for oid, res in owned_as_bar.items():
        if res.get("accepted"):
            accepted_node_ids.add(oid)
    for lid, res in leader_results.items():
        if res.get("accepted"):
            accepted_node_ids.add(lid)
            # arrows / targets linked from leader
            for e in out_edges.get(lid, []):
                if e.get("type") in ("HAS_ARROW", "TARGETS", "POINTS_TO"):
                    if e["target_id"] in nodes:
                        tgt = nodes[e["target_id"]]
                        if tgt.get("type") in (
                            "LeaderArrow",
                            "LeaderTarget",
                            "PhysicalBar",
                            "OwnedEntity",
                        ):
                            if tgt.get("type") in ("LeaderArrow", "LeaderTarget"):
                                accepted_node_ids.add(e["target_id"])
                            elif (bar_results.get(e["target_id"]) or owned_as_bar.get(e["target_id"]) or {}).get(
                                "accepted"
                            ):
                                accepted_node_ids.add(e["target_id"])
    for aid, res in ann_results.items():
        if res.get("accepted"):
            accepted_node_ids.add(aid)
    for sid, res in sem_results.items():
        if res.get("accepted"):
            accepted_node_ids.add(sid)

    accepted_annotations = [
        {
            "id": aid,
            "text": (nodes[aid].get("attributes") or {}).get("clean_text"),
            **ann_results[aid],
        }
        for aid in ann_results
        if ann_results[aid].get("accepted")
    ]
    rejected_annotations = [
        {
            "id": aid,
            "text": (nodes[aid].get("attributes") or {}).get("clean_text"),
            **ann_results[aid],
            **(
                next(
                    (c for c in chains_rejected if c["annotation_id"] == aid),
                    {},
                )
            ),
        }
        for aid in ann_results
        if not ann_results[aid].get("accepted")
    ]

    return {
        "beam": beam_id,
        "model_version": MODEL_VERSION,
        "envelope": envelope,
        "accepted_annotations": accepted_annotations,
        "rejected_annotations": rejected_annotations,
        "accepted_chains": chains_accepted,
        "rejected_chains": chains_rejected,
        "accepted_node_ids": sorted(accepted_node_ids),
        "bar_results": {k: v for k, v in bar_results.items()},
        "leader_results": {k: v for k, v in leader_results.items()},
        "stats": {
            "accepted_annotation_count": len(accepted_annotations),
            "rejected_annotation_count": len(rejected_annotations),
            "accepted_bar_count": sum(1 for v in bar_results.values() if v.get("accepted")),
            "rejected_bar_count": sum(
                1 for v in bar_results.values() if not v.get("accepted")
            ),
            "accepted_leader_count": sum(
                1 for v in leader_results.values() if v.get("accepted")
            ),
            "cross_beam_leakage_count": sum(
                1
                for c in chains_rejected
                if c.get("rejected_rule") == "R5_NEIGHBOUR_REJECT"
                or c.get("neighbour_beam_source")
            ),
        },
    }


def build_scoped_annotations(
    beam_id: str,
    graph: Dict[str, Any],
    ownership: Dict[str, Any],
) -> Dict[str, Any]:
    """BeamScopedAnnotations.json fragment for one beam."""
    allowed = set(ownership.get("accepted_node_ids") or [])
    nodes = [
        n
        for n in (graph.get("nodes") or [])
        if n.get("beam_id") == beam_id and n["id"] in allowed
    ]
    edges = [
        e
        for e in (graph.get("edges") or [])
        if e.get("beam_id") == beam_id
        and e.get("source_id") in allowed
        and e.get("target_id") in allowed
    ]
    anns = [
        {
            "id": n["id"],
            "text": (n.get("attributes") or {}).get("clean_text"),
            "x": (n.get("attributes") or {}).get("x"),
            "y": (n.get("attributes") or {}).get("y"),
            "type": n.get("type"),
        }
        for n in nodes
        if n.get("type") == "Annotation"
    ]
    sems = [
        {
            "id": n["id"],
            "type": n.get("type"),
            "meaning": (n.get("attributes") or {}).get("engineering_meaning"),
            "semantic_type": (n.get("attributes") or {}).get("semantic_type"),
            "text": (n.get("attributes") or {}).get("raw_text"),
        }
        for n in nodes
        if n.get("type")
        in (
            "SemanticFact",
            "DevelopmentLength",
            "SideFaceReinforcement",
            "StirrupNote",
            "SpacerBar",
        )
    ]
    return {
        "beam_id": beam_id,
        "model_version": MODEL_VERSION,
        "annotations": anns,
        "semantics": sems,
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }
