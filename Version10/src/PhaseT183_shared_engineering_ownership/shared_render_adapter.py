"""
T1.8.3 — Runtime effective scoped graph for rendering (owned + shared).
MODEL_VERSION: 9.5.3

Does not mutate stored BeamScopedAnnotations.json.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Set

MODEL_VERSION = "9.5.3"

_RELATED_TYPES = {
    "Annotation",
    "Leader",
    "LeaderArrow",
    "LeaderTarget",
    "SemanticFact",
    "SideFaceReinforcement",
    "DevelopmentLength",
    "StirrupNote",
    "SpacerBar",
}


def _index_graph(graph: Dict[str, Any]):
    nodes = {n["id"]: n for n in (graph.get("nodes") or [])}
    out: Dict[str, List[Dict[str, Any]]] = {}
    for e in graph.get("edges") or []:
        out.setdefault(e["source_id"], []).append(e)
    return nodes, out


def _collect_subgraph(
    annotation_id: str,
    nodes: Dict[str, Dict[str, Any]],
    out_edges: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Collect annotation + leaders + arrows + semantic nodes for one ann."""
    keep: Set[str] = {annotation_id}
    # Outgoing from annotation
    for e in out_edges.get(annotation_id, []):
        if e.get("type") in ("ATTACHED_TO", "DESCRIBES"):
            keep.add(e["target_id"])
    # Leaders → arrows / targets / pointed bars (OwnedEntity optional)
    for lid in list(keep):
        n = nodes.get(lid)
        if not n or n.get("type") != "Leader":
            continue
        for e in out_edges.get(lid, []):
            if e.get("type") in ("HAS_ARROW", "TARGETS", "POINTS_TO"):
                keep.add(e["target_id"])
    # Semantics that INTERPRETS annotation
    for nid, n in nodes.items():
        if n.get("type") not in (
            "SemanticFact",
            "SideFaceReinforcement",
            "DevelopmentLength",
            "StirrupNote",
            "SpacerBar",
        ):
            continue
        for e in out_edges.get(nid, []):
            if e.get("type") == "INTERPRETS" and e.get("target_id") == annotation_id:
                keep.add(nid)

    sub_nodes = []
    for nid in keep:
        n = nodes.get(nid)
        if not n:
            continue
        # Do not inject foreign PhysicalBar / OwnedEntity — avoids bar duplication
        if n.get("type") not in _RELATED_TYPES:
            continue
        sub_nodes.append(copy.deepcopy(n))

    sub_edges = [
        copy.deepcopy(e)
        for e in (out_edges.get(annotation_id) or [])
        if e.get("target_id") in keep
    ]
    for nid in keep:
        for e in out_edges.get(nid, []):
            if e.get("source_id") in keep and e.get("target_id") in keep:
                if e not in sub_edges and not any(
                    x.get("id") == e.get("id") for x in sub_edges if e.get("id")
                ):
                    sub_edges.append(copy.deepcopy(e))

    return {"nodes": sub_nodes, "edges": sub_edges, "node_ids": keep}


def build_effective_scoped(
    beam_id: str,
    base_scoped: Dict[str, Any],
    merge: Dict[str, Any],
    graph: Dict[str, Any],
    *,
    enable_shared: bool = True,
) -> Dict[str, Any]:
    """
    effective_scoped = deepcopy(base_scoped) + shared annotation subgraphs.
    Node ids deduplicated. beam_id on injected nodes retargeted for render context.
    """
    effective = copy.deepcopy(base_scoped or {})
    effective["beam_id"] = beam_id
    effective["model_version"] = MODEL_VERSION
    effective["shared_ownership_enabled"] = enable_shared

    if not enable_shared:
        effective["shared_injected"] = []
        return effective

    nodes_ix, out_edges = _index_graph(graph)
    existing_ids = {n["id"] for n in (effective.get("nodes") or [])}
    injected = []

    for s in merge.get("shared_annotations") or []:
        aid = s.get("id")
        if not aid or aid in existing_ids:
            continue
        sub = _collect_subgraph(aid, nodes_ix, out_edges)
        for n in sub["nodes"]:
            if n["id"] in existing_ids:
                continue
            # Keep original engineering identity; stamp render host
            n = copy.deepcopy(n)
            attrs = n.setdefault("attributes", {})
            attrs["shared_render_host"] = beam_id
            attrs["shared_from_beam"] = s.get("primary_beam")
            attrs["shared_scope_id"] = s.get("scope_id")
            # Do not rewrite beam_id on Annotation — adapter marks host separately
            effective.setdefault("nodes", []).append(n)
            existing_ids.add(n["id"])
        for e in sub["edges"]:
            # Avoid edge dupes
            eid = e.get("id")
            if eid and any(x.get("id") == eid for x in (effective.get("edges") or [])):
                continue
            effective.setdefault("edges", []).append(e)
        injected.append(aid)

        # Ensure annotation list entry
        ann_node = nodes_ix.get(aid)
        if ann_node:
            text = (ann_node.get("attributes") or {}).get("clean_text")
            if not any(a.get("id") == aid for a in (effective.get("annotations") or [])):
                effective.setdefault("annotations", []).append(
                    {
                        "id": aid,
                        "text": text,
                        "x": (ann_node.get("attributes") or {}).get("x"),
                        "y": (ann_node.get("attributes") or {}).get("y"),
                        "type": "Annotation",
                        "source": "shared",
                    }
                )

    effective["shared_injected"] = injected
    effective["node_count"] = len(effective.get("nodes") or [])
    effective["edge_count"] = len(effective.get("edges") or [])
    return effective
