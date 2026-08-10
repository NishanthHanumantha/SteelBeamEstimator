"""
Diagnostic-only counterfactual acceptance policies A–E.
MODEL_VERSION: 10.5.3

These are NOT production engineering rules.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .config import MODEL_VERSION, PHASE_ID

POLICY_DEFS = {
    "A_CURRENT": {
        "label": "CURRENT — exact T18 behaviour",
        "description": "Reproduce existing T18 / R2_LEADER_TIP outcome",
    },
    "B_CHAIN_EVIDENCE": {
        "label": "CHAIN EVIDENCE",
        "description": "continuity AND bar proximity AND target beam context",
    },
    "C_CHAIN_ENDPOINT": {
        "label": "CHAIN + ENDPOINT",
        "description": "B plus endpoint near envelope",
    },
    "D_CHAIN_GEOMETRIC": {
        "label": "CHAIN + GEOMETRIC ALIGNMENT",
        "description": "continuity + context + long/transverse + no neighbour risk",
    },
    "E_STRONG_COMBINED": {
        "label": "STRONG COMBINED EVIDENCE",
        "description": "chain+context+bar AND (endpoint OR long overlap) AND no neighbour risk",
    },
}


def evaluate_policies(trace: Dict[str, Any], scorecard: Dict[str, Any]) -> Dict[str, Any]:
    A = bool(trace.get("r2_tip_in_envelope_ok")) and (
        (trace.get("evaluate_leader_replay") or {}).get("accepted")
        if trace.get("evaluate_leader_replay") is not None
        else bool(trace.get("r2_tip_in_envelope_ok"))
    )
    # Policy A must match existing T18 decision when available
    existing = str(trace.get("existing_t18_decision") or "").upper()
    if existing == "ACCEPTED":
        A = True
    elif existing == "REJECTED":
        A = False

    cont = scorecard["A_chain_continuity"]
    bar = scorecard["B_leader_to_bar_proximity"]
    ctx = scorecard["C_target_beam_context"]
    endp = scorecard["D_endpoint_near_production_envelope"]
    longi = scorecard["F_longitudinal_overlap"]
    trans = scorecard["G_transverse_alignment"]
    inside = scorecard["H_inside_another_beam_envelope"]
    nbr = scorecard["I_neighbour_ambiguity"]

    B = cont and bar and ctx
    C = cont and bar and ctx and endp
    D = cont and ctx and longi and trans and (not nbr) and (not inside)
    E = (
        cont
        and ctx
        and bar
        and (endp or longi)
        and (not nbr)
        and (not inside)
    )

    results = {
        "A_CURRENT": A,
        "B_CHAIN_EVIDENCE": B,
        "C_CHAIN_ENDPOINT": C,
        "D_CHAIN_GEOMETRIC": D,
        "E_STRONG_COMBINED": E,
    }
    changing = [p for p, v in results.items() if v and not A]
    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "beam_id": trace.get("beam_id"),
        "leader_id": trace.get("leader_id"),
        "stable_key": trace.get("stable_key"),
        "current_t18_result": existing or "UNKNOWN",
        "current_rejection_reason": trace.get("exact_r2_rejection_condition")
        or trace.get("existing_ownership_reason"),
        "policy_results": results,
        "policies_that_would_accept": [p for p, v in results.items() if v],
        "evidence_that_changes_result": changing,
        "would_still_be_rejected_under_all": not any(results.values()),
        "neighbour_ambiguity": nbr,
        "inside_other_beam_envelope": inside,
        "diagnostic_only": True,
        "label": "COUNTERFACTUAL — NOT PRODUCTION OWNERSHIP",
    }


def policy_comparison(all_policy_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {p: 0 for p in POLICY_DEFS}
    eligible_counts = {p: 0 for p in POLICY_DEFS}
    for row in all_policy_rows:
        pr = row.get("policy_results") or {}
        for p, v in pr.items():
            if v:
                counts[p] = counts.get(p, 0) + 1
                if row.get("recovery_eligible"):
                    eligible_counts[p] = eligible_counts.get(p, 0) + 1
    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "policy_definitions": POLICY_DEFS,
        "accepted_count_all_23": counts,
        "accepted_count_among_5_eligible": eligible_counts,
        "delta_vs_policy_A": {
            p: counts[p] - counts.get("A_CURRENT", 0) for p in counts
        },
        "note": "Diagnostic counts only — not production ownership changes",
    }
