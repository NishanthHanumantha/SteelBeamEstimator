"""
T1.7 QA diagnostics for AnnotationGraph completeness.
MODEL_VERSION: 9.4.0
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Set

from .graph_models import AnnotationGraph

MODEL_VERSION = "9.4.0"


def _connected_components(g: AnnotationGraph, beam_id: str) -> List[Set[str]]:
    ids = {n["id"] for n in g.nodes.values() if n.get("beam_id") == beam_id}
    adj: Dict[str, Set[str]] = {i: set() for i in ids}
    for e in g.edges:
        if e.get("beam_id") != beam_id:
            continue
        s, t = e["source_id"], e["target_id"]
        if s in adj and t in adj:
            adj[s].add(t)
            adj[t].add(s)
    seen: Set[str] = set()
    comps: List[Set[str]] = []
    for nid in ids:
        if nid in seen:
            continue
        stack = [nid]
        comp: Set[str] = set()
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            comp.add(cur)
            stack.extend(adj[cur] - seen)
        comps.append(comp)
    return comps


def diagnose_beam(g: AnnotationGraph, beam_id: str) -> Dict[str, Any]:
    nodes = [n for n in g.nodes.values() if n.get("beam_id") == beam_id]
    edges = [e for e in g.edges if e.get("beam_id") == beam_id]

    bars = [n for n in nodes if n["type"] == "PhysicalBar"]
    leaders = [n for n in nodes if n["type"] == "Leader"]
    anns = [
        n
        for n in nodes
        if n["type"]
        in (
            "Annotation",
            "Text",
            "Dimension",
            "StirrupNote",
            "SideFaceReinforcement",
            "DevelopmentLength",
        )
    ]
    # Count Annotation nodes specifically + semantic typed nodes
    ann_nodes = [n for n in nodes if n["type"] == "Annotation"]
    semantics = [
        n
        for n in nodes
        if n["type"]
        in (
            "SemanticFact",
            "StirrupNote",
            "SideFaceReinforcement",
            "DevelopmentLength",
            "SpacerBar",
        )
    ]

    # Unresolved leaders: no POINTS_TO PhysicalBar/OwnedEntity
    unresolved_leaders = []
    for L in leaders:
        outs = [
            e
            for e in edges
            if e["source_id"] == L["id"] and e["type"] == "POINTS_TO"
        ]
        bar_hits = [
            e
            for e in outs
            if g.nodes.get(e["target_id"], {}).get("type")
            in ("PhysicalBar", "OwnedEntity")
        ]
        if not bar_hits:
            unresolved_leaders.append(L["id"])

    # Unattached annotations: no ATTACHED_TO leader and no DESCRIBES bar
    unattached_anns = []
    for a in ann_nodes:
        outs = [e for e in edges if e["source_id"] == a["id"]]
        has_leader = any(e["type"] == "ATTACHED_TO" for e in outs)
        has_desc = any(e["type"] == "DESCRIBES" for e in outs)
        if not has_leader and not has_desc:
            unattached_anns.append(
                {
                    "id": a["id"],
                    "text": (a.get("attributes") or {}).get("clean_text"),
                }
            )

    # Dangling nodes: degree 0 (excluding Beam itself which always has edges)
    degree: Dict[str, int] = {n["id"]: 0 for n in nodes}
    for e in edges:
        if e["source_id"] in degree:
            degree[e["source_id"]] += 1
        if e["target_id"] in degree:
            degree[e["target_id"]] += 1
    dangling = [
        nid
        for nid, deg in degree.items()
        if deg == 0 and g.nodes[nid]["type"] != "Beam"
    ]

    comps = _connected_components(g, beam_id)
    # Completeness: fraction of annotations that have semantic + (leader or describes)
    complete_anns = 0
    expected_flags = {
        "has_top_bar_callout": False,
        "has_side_face": False,
        "has_ld": False,
        "has_stirrup": False,
        "has_multi_leader_chain": False,
    }
    for a in ann_nodes:
        outs = [e for e in edges if e["source_id"] == a["id"]]
        # INTERPRETS is semantic → annotation (source=sem, target=ann)
        has_sem = any(
            e["target_id"] == a["id"] and e["type"] == "INTERPRETS" for e in edges
        )
        has_link = any(
            e["type"] in ("ATTACHED_TO", "DESCRIBES", "PROPAGATES_TO", "MATCHES_ENTITY")
            for e in outs
        )
        if has_sem and has_link:
            complete_anns += 1
        text = str((a.get("attributes") or {}).get("clean_text") or "").upper()
        if re_bar_callout(text) and "SIDE" not in text:
            expected_flags["has_top_bar_callout"] = True
        if "SIDE FACE" in text or "SIDE.FACE" in text:
            expected_flags["has_side_face"] = True
        if re.search(r"\bLD\b", text) or "DEVELOPMENT" in text:
            expected_flags["has_ld"] = True
        if "@" in text and "L" in text.replace(" ", ""):
            expected_flags["has_stirrup"] = True

    # Multi-leader chains: annotations with ATTACHED_TO and that leader POINTS_TO bar
    chain_count = 0
    for a in ann_nodes:
        for e in edges:
            if e["source_id"] != a["id"] or e["type"] != "ATTACHED_TO":
                continue
            lid = e["target_id"]
            if any(
                ee["source_id"] == lid
                and ee["type"] == "POINTS_TO"
                and g.nodes.get(ee["target_id"], {}).get("type")
                in ("PhysicalBar", "OwnedEntity")
                for ee in edges
            ):
                chain_count += 1
    expected_flags["has_multi_leader_chain"] = chain_count >= 2

    n_ann = max(len(ann_nodes), 1)
    completeness = round(100.0 * complete_anns / n_ann, 2)

    semantic_types = {}
    for s in semantics:
        st = (s.get("attributes") or {}).get("semantic_type") or s["type"]
        semantic_types[st] = semantic_types.get(st, 0) + 1

    return {
        "beam_id": beam_id,
        "physical_bars": len(bars),
        "leader_count": len(leaders),
        "annotation_count": len(ann_nodes),
        "semantic_count": len(semantics),
        "semantic_types": semantic_types,
        "owned_entity_count": sum(1 for n in nodes if n["type"] == "OwnedEntity"),
        "edge_count": len(edges),
        "unresolved_leaders": unresolved_leaders,
        "unresolved_leader_count": len(unresolved_leaders),
        "unattached_annotations": unattached_anns,
        "unattached_annotation_count": len(unattached_anns),
        "dangling_nodes": dangling,
        "dangling_count": len(dangling),
        "disconnected_components": len(comps),
        "largest_component_size": max((len(c) for c in comps), default=0),
        "graph_completeness_pct": completeness,
        "leader_bar_chains": chain_count,
        "validation_flags": expected_flags,
        "annotation_texts": [
            (a.get("attributes") or {}).get("clean_text") for a in ann_nodes
        ],
    }


def re_bar_callout(text: str) -> bool:
    return bool(re.search(r"\d\s*[-–]?\s*[YTH]?\s*\d{1,2}\b", text, re.I))


def diagnose_graph(
    g: AnnotationGraph, beam_ids: List[str]
) -> Dict[str, Any]:
    by_beam = {bid: diagnose_beam(g, bid) for bid in beam_ids}
    return {
        "model_version": MODEL_VERSION,
        "phase_id": "T1.7",
        "beam_count": len(beam_ids),
        "by_beam": by_beam,
        "totals": {
            "physical_bars": sum(v["physical_bars"] for v in by_beam.values()),
            "leaders": sum(v["leader_count"] for v in by_beam.values()),
            "annotations": sum(v["annotation_count"] for v in by_beam.values()),
            "semantics": sum(v["semantic_count"] for v in by_beam.values()),
            "unresolved_leaders": sum(
                v["unresolved_leader_count"] for v in by_beam.values()
            ),
            "unattached_annotations": sum(
                v["unattached_annotation_count"] for v in by_beam.values()
            ),
        },
    }
