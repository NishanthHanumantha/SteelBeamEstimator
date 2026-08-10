"""
Bridge P2 leaders into existing T18 ownership results (read-only).
MODEL_VERSION: 10.5.2
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from PhaseT18_beam_ownership.ownership_rules import (
    evaluate_annotation_chain,
    evaluate_leader,
)


def index_graph(graph: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    nodes = {n["id"]: n for n in (graph.get("nodes") or []) if n.get("id")}
    edges = list(graph.get("edges") or [])
    return nodes, edges


def production_accepted_index(
    beam_ownership: Dict[str, Any], priority_beams: List[str]
) -> Dict[str, Set[str]]:
    by_beam = (beam_ownership or {}).get("by_beam") or {}
    return {
        bid: set((by_beam.get(bid) or {}).get("accepted_node_ids") or [])
        for bid in priority_beams
    }


def existing_engine_outcome_for_leader(
    *,
    beam_id: str,
    entity_id: str,
    entity_type: Optional[str],
    beam_own: Dict[str, Any],
    nodes: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Query existing T18 ownership for a leader / annotation.

    Prefer production leader_results / rejected_annotations.
    Optionally re-invoke evaluate_leader only when missing from production.
    """
    accepted_ids = set(beam_own.get("accepted_node_ids") or [])
    leader_results = beam_own.get("leader_results") or {}
    envelope = beam_own.get("envelope") or {}
    already_accepted = entity_id in accepted_ids

    if already_accepted:
        lr = leader_results.get(entity_id) or {}
        return {
            "existing_ownership_result": "ACCEPTED",
            "existing_ownership_score": lr.get("ownership_score", 1.0),
            "final_ownership_decision": "ACCEPTED",
            "ownership_reason": "already_in_production_accepted_node_ids",
            "rejected_rule": None,
            "already_in_production_candidate_pool": True,
            "already_in_t18_scoring_pool": True,
            "engine_path": "t18_accepted_node_ids",
            "engine_input_id": entity_id,
            "parent_leader_id": entity_id if str(entity_id).startswith("LDR::") else None,
            "qa43_assigned_ownership": False,
            "evaluate_invoked": False,
            "evaluate_result": lr or None,
        }

    # Leader path
    if entity_type == "Leader" or str(entity_id).startswith("LDR::"):
        lr = leader_results.get(entity_id)
        if lr is not None:
            accepted = bool(lr.get("accepted"))
            return {
                "existing_ownership_result": "ACCEPTED" if accepted else "REJECTED",
                "existing_ownership_score": lr.get("ownership_score", 0.0),
                "final_ownership_decision": "ACCEPTED" if accepted else "REJECTED",
                "ownership_reason": lr.get("ownership_reason"),
                "rejected_rule": lr.get("rejected_rule"),
                "already_in_production_candidate_pool": False,
                "already_in_t18_scoring_pool": True,
                "engine_path": "t18_leader_results",
                "engine_input_id": entity_id,
                "parent_leader_id": entity_id,
                "qa43_assigned_ownership": False,
                "evaluate_invoked": False,
                "evaluate_result": lr,
            }
        # Missing from production — invoke existing evaluate_leader (read-only)
        node = nodes.get(entity_id)
        if node and envelope:
            eval_result = evaluate_leader(node, envelope, None)
            accepted = bool(eval_result.get("accepted"))
            return {
                "existing_ownership_result": "ACCEPTED" if accepted else "REJECTED",
                "existing_ownership_score": eval_result.get("ownership_score", 0.0),
                "final_ownership_decision": "ACCEPTED" if accepted else "REJECTED",
                "ownership_reason": eval_result.get("ownership_reason"),
                "rejected_rule": eval_result.get("rejected_rule"),
                "already_in_production_candidate_pool": False,
                "already_in_t18_scoring_pool": False,
                "engine_path": "evaluate_leader",
                "engine_input_id": entity_id,
                "parent_leader_id": entity_id,
                "qa43_assigned_ownership": False,
                "evaluate_invoked": True,
                "evaluate_result": eval_result,
            }

    # Annotation path (e.g. R3 chain failure)
    if entity_type == "Annotation" or str(entity_id).startswith("ANN"):
        for ann in beam_own.get("rejected_annotations") or []:
            if ann.get("id") == entity_id:
                return {
                    "existing_ownership_result": "REJECTED",
                    "existing_ownership_score": ann.get("ownership_score", 0.0),
                    "final_ownership_decision": "REJECTED",
                    "ownership_reason": ann.get("ownership_reason"),
                    "rejected_rule": ann.get("rejected_rule"),
                    "already_in_production_candidate_pool": False,
                    "already_in_t18_scoring_pool": True,
                    "engine_path": "t18_rejected_annotations",
                    "engine_input_id": entity_id,
                    "parent_leader_id": (ann.get("leaders") or [None])[0],
                    "qa43_assigned_ownership": False,
                    "evaluate_invoked": False,
                    "evaluate_result": ann,
                }
        for ann in beam_own.get("accepted_annotations") or []:
            if ann.get("id") == entity_id:
                return {
                    "existing_ownership_result": "ACCEPTED",
                    "existing_ownership_score": ann.get("ownership_score", 0.0),
                    "final_ownership_decision": "ACCEPTED",
                    "ownership_reason": ann.get("ownership_reason"),
                    "rejected_rule": None,
                    "already_in_production_candidate_pool": True,
                    "already_in_t18_scoring_pool": True,
                    "engine_path": "t18_accepted_annotations",
                    "engine_input_id": entity_id,
                    "parent_leader_id": (ann.get("leaders") or [None])[0],
                    "qa43_assigned_ownership": False,
                    "evaluate_invoked": False,
                    "evaluate_result": ann,
                }
        node = nodes.get(entity_id)
        if node and envelope:
            eval_result = evaluate_annotation_chain(
                node,
                envelope,
                leader_result=None,
                bar_result=None,
                describes_owned_bar=False,
                sem_node=None,
            )
            accepted = bool(eval_result.get("accepted"))
            return {
                "existing_ownership_result": "ACCEPTED" if accepted else "REJECTED",
                "existing_ownership_score": eval_result.get("ownership_score", 0.0),
                "final_ownership_decision": "ACCEPTED" if accepted else "REJECTED",
                "ownership_reason": eval_result.get("ownership_reason"),
                "rejected_rule": eval_result.get("rejected_rule"),
                "already_in_production_candidate_pool": False,
                "already_in_t18_scoring_pool": False,
                "engine_path": "evaluate_annotation_chain",
                "engine_input_id": entity_id,
                "parent_leader_id": None,
                "qa43_assigned_ownership": False,
                "evaluate_invoked": True,
                "evaluate_result": eval_result,
            }

    return {
        "existing_ownership_result": "UNKNOWN",
        "existing_ownership_score": None,
        "final_ownership_decision": "UNRESOLVED",
        "ownership_reason": "no_existing_engine_path",
        "rejected_rule": None,
        "already_in_production_candidate_pool": False,
        "already_in_t18_scoring_pool": False,
        "engine_path": "none",
        "engine_input_id": entity_id,
        "parent_leader_id": None,
        "qa43_assigned_ownership": False,
        "evaluate_invoked": False,
        "evaluate_result": None,
    }
