"""
Additive effective-ownership overlay (does not mutate ownership_rules / R2).
MODEL_VERSION: 10.5.5
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Set, Tuple

from PhaseT18_beam_ownership.ownership_filter import build_scoped_annotations

from .config import MODEL_VERSION, PHASE_ID, PRODUCTION_POLICY, PROPAGATION_EDGE_TYPES


def _node_index(graph: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {n["id"]: n for n in (graph.get("nodes") or []) if n.get("id")}


def _leader_graph_children(
    graph: Dict[str, Any], leader_id: str
) -> List[Dict[str, Any]]:
    """Direct graph-supported children via HAS_ARROW / TARGETS (existing edges only)."""
    out: List[Dict[str, Any]] = []
    for n in (graph.get("nodes") or []):
        if n.get("id") != leader_id:
            continue
        for rel in n.get("relationships") or []:
            if rel.get("type") not in PROPAGATION_EDGE_TYPES:
                continue
            if rel.get("direction") != "out":
                continue
            other = rel.get("other_id")
            if other:
                out.append(
                    {
                        "entity_id": other,
                        "relationship": rel.get("type"),
                        "edge_id": rel.get("edge_id"),
                        "reason": rel.get("reason"),
                    }
                )
    # Also scan edges
    for e in graph.get("edges") or []:
        if e.get("source_id") != leader_id:
            continue
        if e.get("type") not in PROPAGATION_EDGE_TYPES:
            continue
        tid = e.get("target_id")
        if tid and not any(x["entity_id"] == tid for x in out):
            out.append(
                {
                    "entity_id": tid,
                    "relationship": e.get("type"),
                    "edge_id": e.get("id") or e.get("edge_id"),
                    "reason": e.get("reason") or "graph_edge",
                }
            )
    return out


def apply_overlay(
    *,
    baseline_ownership: Dict[str, Any],
    graph: Dict[str, Any],
    accepted_candidates: List[Dict[str, Any]],
    mode: str,
) -> Dict[str, Any]:
    """
    Build controlled BeamOwnership deepcopy.

    mode BASELINE/OFF → exact copy, no overlay.
    mode CONTROLLED → add only gated E candidates (+ graph-supported ARR/LTGT).
    """
    owned = copy.deepcopy(baseline_ownership)
    owned["phase_id"] = PHASE_ID
    owned["model_version"] = MODEL_VERSION
    owned["ownership_mode"] = mode
    owned["overlay_label"] = (
        "BASELINE_T18_UNCHANGED"
        if mode in ("OFF", "BASELINE")
        else "T18_PLUS_P22_E_STRONG_COMBINED"
    )
    owned["historical_t18_preserved"] = True

    migrations: List[Dict[str, Any]] = []
    propagation: List[Dict[str, Any]] = []

    if mode in ("OFF", "BASELINE") or not accepted_candidates:
        return {
            "ownership": owned,
            "migrations": migrations,
            "propagation": propagation,
            "added_entity_ids": [],
        }

    nodes = _node_index(graph)
    by_beam = owned.setdefault("by_beam", {})
    added: List[str] = []

    for cand in accepted_candidates:
        bid = str(cand.get("beam_id") or "")
        lid = str(cand.get("leader_id") or "")
        sk = str(cand.get("stable_key") or f"{bid}::{lid}")
        beam = by_beam.get(bid)
        if not beam:
            continue

        accepted_ids: Set[str] = set(beam.get("accepted_node_ids") or [])
        leader_results = beam.setdefault("leader_results", {})
        was_accepted = lid in accepted_ids

        # Contam re-check (fail closed)
        if cand.get("neighbour_ambiguity") or cand.get("inside_other_beam_envelope"):
            continue

        if not was_accepted:
            accepted_ids.add(lid)
            added.append(f"{bid}::{lid}")
            leader_results[lid] = {
                "accepted": True,
                "accepted_rules": [PRODUCTION_POLICY],
                "rejected_rule": None,
                "ownership_reason": cand.get("enhanced_reason")
                or "strong_chain_bar_context_with_endpoint_or_longitudinal_evidence",
                "ownership_score": 1.0,
                "source": "P2.2",
                "recovery_policy": PRODUCTION_POLICY,
                "overlay": True,
            }
            migrations.append(
                {
                    "entity_id": lid,
                    "entity_type": "Leader",
                    "beam_id": bid,
                    "stable_key": sk,
                    "baseline_status": "REJECTED",
                    "controlled_status": "ACCEPTED",
                    "source": "P2.2",
                    "recovery_policy": PRODUCTION_POLICY,
                    "reason": cand.get("enhanced_reason"),
                    "contamination_checks": {
                        "neighbour_ambiguity": bool(cand.get("neighbour_ambiguity")),
                        "inside_other_beam_envelope": bool(
                            cand.get("inside_other_beam_envelope")
                        ),
                        "chain_continuity": bool(cand.get("chain_continuity")),
                        "bar_proximity": bool(cand.get("bar_proximity")),
                        "target_beam_context": bool(cand.get("target_beam_context")),
                        "endpoint_near_envelope": bool(
                            cand.get("endpoint_near_envelope")
                        ),
                        "longitudinal_overlap": bool(cand.get("longitudinal_overlap")),
                    },
                    "confidence": cand.get("recovery_potential") or "HIGH",
                }
            )

        # Graph-supported ARR / LTGT children
        children = _leader_graph_children(graph, lid)
        child_adds = []
        for ch in children:
            eid = ch["entity_id"]
            n = nodes.get(eid) or {}
            etype = n.get("type") or "Unknown"
            prev = "ACCEPTED" if eid in accepted_ids else "REJECTED"
            if eid not in accepted_ids:
                accepted_ids.add(eid)
                added.append(f"{bid}::{eid}")
                child_adds.append(eid)
                migrations.append(
                    {
                        "entity_id": eid,
                        "entity_type": etype,
                        "beam_id": bid,
                        "stable_key": f"{bid}::{eid}",
                        "baseline_status": prev,
                        "controlled_status": "ACCEPTED",
                        "source": "P2.2",
                        "recovery_policy": PRODUCTION_POLICY,
                        "reason": (
                            f"graph_propagation_from_{lid}_via_{ch.get('relationship')}"
                        ),
                        "contamination_checks": {
                            "parent_leader": lid,
                            "relationship": ch.get("relationship"),
                            "edge_id": ch.get("edge_id"),
                        },
                        "confidence": "GRAPH_SUPPORTED",
                    }
                )

        # Linked annotation / bars already owned — record propagation trace only
        linked_anns = []
        linked_bars = []
        for ch in (beam.get("accepted_chains") or []):
            if lid in (ch.get("leaders") or []):
                aid = ch.get("annotation_id")
                if aid:
                    linked_anns.append(aid)
                for d in ch.get("describes") or []:
                    if str(d).startswith("BAR"):
                        linked_bars.append(d)

        propagation.append(
            {
                "recovered_leader": lid,
                "beam_id": bid,
                "stable_key": sk,
                "linked_annotations": sorted(set(linked_anns)),
                "linked_physical_bars": sorted(set(linked_bars)),
                "propagated_graph_children": child_adds,
                "annotation_baseline_owned": {
                    a: a in set(beam.get("accepted_node_ids") or [])
                    or a in accepted_ids
                    for a in sorted(set(linked_anns))
                },
                "bar_baseline_owned": {
                    b: b in set(beam.get("accepted_node_ids") or []) or b in accepted_ids
                    for b in sorted(set(linked_bars))
                },
                "nodes": [
                    {
                        "entity_id": lid,
                        "entity_type": "Leader",
                        "previous_ownership": "REJECTED" if not was_accepted else "ACCEPTED",
                        "new_ownership": "ACCEPTED",
                        "evidence_source": "P2.2",
                        "relationship_source": "E_STRONG_COMBINED",
                    },
                    *[
                        {
                            "entity_id": eid,
                            "entity_type": (nodes.get(eid) or {}).get("type"),
                            "previous_ownership": "REJECTED",
                            "new_ownership": "ACCEPTED",
                            "evidence_source": "P2.2",
                            "relationship_source": next(
                                (
                                    c["relationship"]
                                    for c in children
                                    if c["entity_id"] == eid
                                ),
                                "HAS_ARROW/TARGETS",
                            ),
                        }
                        for eid in child_adds
                    ],
                    *[
                        {
                            "entity_id": a,
                            "entity_type": "Annotation",
                            "previous_ownership": "ACCEPTED",
                            "new_ownership": "ACCEPTED",
                            "evidence_source": "T18_existing",
                            "relationship_source": "accepted_chain_via_leader",
                        }
                        for a in sorted(set(linked_anns))
                    ],
                    *[
                        {
                            "entity_id": b,
                            "entity_type": "PhysicalBar",
                            "previous_ownership": "ACCEPTED",
                            "new_ownership": "ACCEPTED",
                            "evidence_source": "T18_existing",
                            "relationship_source": "accepted_chain_describes",
                        }
                        for b in sorted(set(linked_bars))
                    ],
                ],
            }
        )

        beam["accepted_node_ids"] = sorted(accepted_ids)
        # Update stats lightly
        stats = beam.setdefault("stats", {})
        stats["accepted_leaders"] = sum(
            1
            for nid in beam["accepted_node_ids"]
            if str(nid).startswith("LDR::")
        )

    return {
        "ownership": owned,
        "migrations": sorted(
            migrations,
            key=lambda r: (
                str(r.get("beam_id") or ""),
                str(r.get("entity_id") or ""),
            ),
        ),
        "propagation": sorted(
            propagation,
            key=lambda r: (
                str(r.get("beam_id") or ""),
                str(r.get("recovered_leader") or ""),
            ),
        ),
        "added_entity_ids": sorted(added),
    }


def rebuild_scoped(
    ownership: Dict[str, Any],
    graph: Dict[str, Any],
    beam_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    by_beam = ownership.get("by_beam") or {}
    ids = beam_ids or sorted(by_beam.keys())
    out = {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "by_beam": {},
    }
    for bid in ids:
        own = by_beam.get(bid)
        if not own:
            continue
        out["by_beam"][bid] = build_scoped_annotations(bid, graph, own)
    return out


def ownership_counts(ownership: Dict[str, Any], beam_ids: List[str]) -> Dict[str, Any]:
    by_beam = ownership.get("by_beam") or {}
    leaders = anns = bars = sems = total = 0
    for bid in beam_ids:
        ids = (by_beam.get(bid) or {}).get("accepted_node_ids") or []
        total += len(ids)
        for nid in ids:
            s = str(nid)
            if s.startswith("LDR::"):
                leaders += 1
            elif s.startswith("ANN"):
                anns += 1
            elif s.startswith("BAR"):
                bars += 1
            elif s.startswith("SEM") or "Semantic" in s:
                sems += 1
    return {
        "beams": len([b for b in beam_ids if b in by_beam]),
        "accepted_node_total": total,
        "accepted_leaders": leaders,
        "accepted_annotations": anns,
        "accepted_physical_bars": bars,
        "accepted_semantic_annotations": sems,
    }
