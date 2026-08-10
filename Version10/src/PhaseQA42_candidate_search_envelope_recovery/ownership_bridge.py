"""
Bridge recovery candidates into the EXISTING T18 ownership engine (read-only).

Does NOT modify ownership rules.
Does NOT write BeamOwnership.json.
MODEL_VERSION: 10.5.1
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from PhaseT18_beam_ownership.ownership_rules import evaluate_leader


def index_graph(graph: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    nodes = {n["id"]: n for n in (graph.get("nodes") or []) if n.get("id")}
    edges = list(graph.get("edges") or [])
    return nodes, edges


def build_parent_leader_map(edges: List[Dict[str, Any]], nodes: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """Map ARR/LTGT entity_id → parent LDR entity_id using existing graph edges/attrs."""
    parent: Dict[str, str] = {}
    for e in edges:
        et = e.get("type")
        if et == "HAS_ARROW":
            parent[str(e["target_id"])] = str(e["source_id"])
        elif et == "TARGETS":
            parent[str(e["target_id"])] = str(e["source_id"])
    # Attribute fallback
    for nid, n in nodes.items():
        if n.get("type") in ("LeaderArrow", "LeaderTarget"):
            if nid in parent:
                continue
            lid = (n.get("attributes") or {}).get("leader_id")
            if lid:
                lid_s = str(lid)
                if not lid_s.startswith("LDR::"):
                    lid_s = f"LDR::{lid_s}"
                parent[nid] = lid_s
    return parent


def production_accepted_index(
    beam_ownership: Dict[str, Any], priority_beams: List[str]
) -> Dict[str, Set[str]]:
    by_beam = (beam_ownership or {}).get("by_beam") or {}
    out: Dict[str, Set[str]] = {}
    for bid in priority_beams:
        own = by_beam.get(bid) or {}
        out[bid] = set(own.get("accepted_node_ids") or [])
    return out


def existing_engine_outcome_for_entity(
    *,
    beam_id: str,
    entity_id: str,
    entity_type: Optional[str],
    beam_own: Dict[str, Any],
    nodes: Dict[str, Dict[str, Any]],
    parent_leaders: Dict[str, str],
    re_evaluate_leader_if_missing: bool = True,
) -> Dict[str, Any]:
    """
    Query / invoke existing ownership engine for a recovery candidate.

    Flow:
      - Beam / ARR / LTGT already in accepted_node_ids → ACCEPTED (production)
      - Otherwise evaluate parent Leader via evaluate_leader (existing rule R2/R5)
      - Satellite acceptance follows T18 promotion rule (leader accepted ⇒ satellite accepted)
    """
    accepted_ids = set(beam_own.get("accepted_node_ids") or [])
    leader_results = beam_own.get("leader_results") or {}
    bar_results = beam_own.get("bar_results") or {}
    envelope = beam_own.get("envelope") or {}

    already_present = entity_id in accepted_ids
    scorable_via = None
    engine_input_id = entity_id
    eval_result: Optional[Dict[str, Any]] = None

    if entity_type == "Beam":
        scorable_via = "t18_beam_node_always_accepted"
        accepted = entity_id in accepted_ids
        score = 1.0 if accepted else 0.0
        reason = "beam_node_in_accepted_node_ids" if accepted else "beam_node_missing_from_accepted"
        return {
            "existing_ownership_result": "ACCEPTED" if accepted else "REJECTED",
            "existing_ownership_score": score,
            "final_ownership_decision": "ACCEPTED" if accepted else "REJECTED",
            "ownership_reason": reason,
            "rejected_rule": None if accepted else "NOT_IN_PRODUCTION_ACCEPTED",
            "already_in_production_candidate_pool": already_present,
            "engine_path": scorable_via,
            "engine_input_id": engine_input_id,
            "qa42_assigned_ownership": False,
            "evaluate_leader_invoked": False,
            "evaluate_result": None,
        }

    # LeaderArrow / LeaderTarget → parent leader
    if entity_type in ("LeaderArrow", "LeaderTarget") or entity_id.startswith(
        ("ARR::", "LTGT::")
    ):
        lid = parent_leaders.get(entity_id)
        if not lid:
            attrs = (nodes.get(entity_id) or {}).get("attributes") or {}
            raw = attrs.get("leader_id")
            if raw:
                lid = str(raw) if str(raw).startswith("LDR::") else f"LDR::{raw}"
        engine_input_id = lid or entity_id
        scorable_via = "t18_satellite_via_evaluate_leader"

        if already_present:
            # Production already promoted satellite when parent leader accepted
            lr = leader_results.get(lid) if lid else None
            return {
                "existing_ownership_result": "ACCEPTED",
                "existing_ownership_score": (lr or {}).get("ownership_score", 1.0),
                "final_ownership_decision": "ACCEPTED",
                "ownership_reason": "already_in_production_accepted_node_ids",
                "rejected_rule": None,
                "already_in_production_candidate_pool": True,
                "engine_path": scorable_via,
                "engine_input_id": engine_input_id,
                "parent_leader_id": lid,
                "qa42_assigned_ownership": False,
                "evaluate_leader_invoked": False,
                "evaluate_result": lr,
            }

        # Not already present — invoke existing evaluate_leader
        lr = leader_results.get(lid) if lid else None
        if lr is not None and not re_evaluate_leader_if_missing:
            eval_result = lr
        elif lid and lid in nodes and envelope:
            # Determine pointed bar acceptance from production bar_results
            pointed = None
            # Prefer production leader_results if present
            if lr is not None:
                eval_result = lr
            else:
                # Re-evaluate with existing rule using production envelope (unchanged)
                pointed_bar_result = None
                # Heuristic: if any accepted bar exists, pass a synthetic accepted pointer
                # only when production leader_results already recorded acceptance path.
                # Safer: pointed=None → evaluate tip only (matches evaluate_leader when no bar)
                eval_result = evaluate_leader(nodes[lid], envelope, pointed_bar_result)
        else:
            eval_result = {
                "accepted": False,
                "ownership_score": 0.0,
                "ownership_reason": "parent_leader_missing",
                "rejected_rule": "R2_LEADER_TIP",
            }

        accepted = bool((eval_result or {}).get("accepted"))
        return {
            "existing_ownership_result": "ACCEPTED" if accepted else "REJECTED",
            "existing_ownership_score": (eval_result or {}).get("ownership_score", 0.0),
            "final_ownership_decision": "ACCEPTED" if accepted else "REJECTED",
            "ownership_reason": (eval_result or {}).get("ownership_reason"),
            "rejected_rule": (eval_result or {}).get("rejected_rule"),
            "already_in_production_candidate_pool": False,
            "engine_path": scorable_via,
            "engine_input_id": engine_input_id,
            "parent_leader_id": lid,
            "qa42_assigned_ownership": False,
            "evaluate_leader_invoked": lr is None and lid in nodes,
            "evaluate_result": eval_result,
        }

    # PhysicalBar / Leader / Annotation — direct production lookup
    if entity_id in bar_results:
        br = bar_results[entity_id]
        accepted = bool(br.get("accepted"))
        return {
            "existing_ownership_result": "ACCEPTED" if accepted else "REJECTED",
            "existing_ownership_score": br.get("ownership_score", 0.0),
            "final_ownership_decision": "ACCEPTED" if accepted else "REJECTED",
            "ownership_reason": br.get("ownership_reason"),
            "rejected_rule": br.get("rejected_rule"),
            "already_in_production_candidate_pool": already_present or entity_id in bar_results,
            "engine_path": "t18_bar_results",
            "engine_input_id": entity_id,
            "qa42_assigned_ownership": False,
            "evaluate_leader_invoked": False,
            "evaluate_result": br,
        }
    if entity_id in leader_results:
        lr = leader_results[entity_id]
        accepted = bool(lr.get("accepted"))
        return {
            "existing_ownership_result": "ACCEPTED" if accepted else "REJECTED",
            "existing_ownership_score": lr.get("ownership_score", 0.0),
            "final_ownership_decision": "ACCEPTED" if accepted else "REJECTED",
            "ownership_reason": lr.get("ownership_reason"),
            "rejected_rule": lr.get("rejected_rule"),
            "already_in_production_candidate_pool": already_present or True,
            "engine_path": "t18_leader_results",
            "engine_input_id": entity_id,
            "qa42_assigned_ownership": False,
            "evaluate_leader_invoked": False,
            "evaluate_result": lr,
        }

    return {
        "existing_ownership_result": "UNKNOWN",
        "existing_ownership_score": None,
        "final_ownership_decision": "UNRESOLVED",
        "ownership_reason": "no_existing_engine_path",
        "rejected_rule": None,
        "already_in_production_candidate_pool": already_present,
        "engine_path": "none",
        "engine_input_id": entity_id,
        "qa42_assigned_ownership": False,
        "evaluate_leader_invoked": False,
        "evaluate_result": None,
    }
