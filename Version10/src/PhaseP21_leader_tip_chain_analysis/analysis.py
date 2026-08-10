"""
End-to-end P2.1 diagnostic analysis (no production mutations).
MODEL_VERSION: 10.5.3
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from PhaseQA31_pipeline_diagnostics.artefact_locator import PRIORITY_FOURTH_BEAMS

from .config import MODEL_VERSION, PHASE_ID
from .contamination import assess_contamination, contamination_summary
from .excluded import classify_excluded, summarize_excluded
from .impact import candidate_impact
from .policies import evaluate_policies, policy_comparison
from .r2_trace import index_graph, reconstruct_r2
from .root_cause import build_root_cause
from .scorecard import build_scorecard


def run_analysis(
    *,
    population: Dict[str, Any],
    beam_ownership: Dict[str, Any],
    graph: Dict[str, Any],
    priority_beams: Sequence[str] = PRIORITY_FOURTH_BEAMS,
) -> Dict[str, Any]:
    nodes, edges = index_graph(graph or {})
    by_beam = (beam_ownership or {}).get("by_beam") or {}
    all_envelopes = {
        b: (by_beam.get(b) or {}).get("envelope") or {} for b in priority_beams
    }
    qa41_by = population.get("qa41_by_key") or {}
    la_by = population.get("leader_audit_by_key") or {}

    traces: List[Dict[str, Any]] = []
    scorecards: List[Dict[str, Any]] = []
    policy_rows: List[Dict[str, Any]] = []
    contam_rows: List[Dict[str, Any]] = []
    decision_traces: List[Dict[str, Any]] = []
    counterfactual_ownership: List[Dict[str, Any]] = []
    excluded_rows: List[Dict[str, Any]] = []

    for row in population.get("leaders") or []:
        sk = str(row.get("stable_key") or f"{row.get('beam_id')}::{row.get('entity_id')}")
        bid = str(row.get("beam_id") or "")
        trace = reconstruct_r2(
            qa43_row=row,
            qa41_row=qa41_by.get(sk),
            leader_audit=la_by.get(sk),
            beam_own=by_beam.get(bid) or {},
            nodes=nodes,
            edges=edges,
            all_envelopes=all_envelopes,
            priority_beams=list(priority_beams),
        )
        sc = build_scorecard(trace)
        pol = evaluate_policies(trace, sc)
        pol["recovery_eligible"] = bool(row.get("recovery_eligible"))
        cont = assess_contamination(trace, sc)

        traces.append(trace)
        scorecards.append(sc)
        policy_rows.append(pol)
        contam_rows.append(cont)

        decision_traces.append(
            {
                "stable_key": sk,
                "beam_id": bid,
                "leader_id": row.get("entity_id"),
                "path": [
                    "Leader",
                    "Leader geometry",
                    "Leader tip",
                    "Leader chain continuity",
                    "Leader → bar proximity",
                    "Target beam context",
                    "Production envelope/support test (tip_in_envelope)",
                    "R2_LEADER_TIP",
                    "Final T18 ownership decision",
                ],
                "tip_in_envelope_ok": trace.get("r2_tip_in_envelope_ok"),
                "exact_r2_condition": trace.get("exact_r2_rejection_condition"),
                "existing_t18_decision": trace.get("existing_t18_decision"),
                "existing_rejected_rule": trace.get("existing_rejected_rule"),
                "existing_ownership_reason": trace.get("existing_ownership_reason"),
                "evaluate_leader_replay": trace.get("evaluate_leader_replay"),
            }
        )

        # Counterfactual ownership rows per policy that differs from current
        for pname, accepted in (pol.get("policy_results") or {}).items():
            current = trace.get("existing_t18_decision")
            cf_decision = "ACCEPTED" if accepted else "REJECTED"
            changed = (current == "REJECTED" and accepted) or (
                current == "ACCEPTED" and not accepted
            )
            counterfactual_ownership.append(
                {
                    "label": "COUNTERFACTUAL — NOT PRODUCTION OWNERSHIP",
                    "stable_key": sk,
                    "beam_id": bid,
                    "leader_id": row.get("entity_id"),
                    "current_owner": None if current == "REJECTED" else bid,
                    "counterfactual_owner": bid if accepted else None,
                    "current_decision": current,
                    "counterfactual_decision": cf_decision,
                    "policy_used": pname,
                    "evidence_supporting_change": pol.get("evidence_that_changes_result")
                    if changed
                    else [],
                    "contamination_status": cont.get("cross_beam_contamination_risk"),
                    "confidence_category": row.get("recovery_potential"),
                    "decision_changed_counterfactually": changed,
                }
            )

        if not row.get("recovery_eligible"):
            excluded_rows.append(classify_excluded(trace, sc, pol))

    comparison = policy_comparison(policy_rows)
    contam_sum = contamination_summary(contam_rows)
    excluded_sum = summarize_excluded(excluded_rows)

    eligible_keys = [
        str(r.get("stable_key"))
        for r in (population.get("eligible") or [])
    ]
    elig_traces = [t for t in traces if t.get("stable_key") in eligible_keys]
    elig_pols = [p for p in policy_rows if p.get("stable_key") in eligible_keys]
    elig_cont = [c for c in contam_rows if c.get("stable_key") in eligible_keys]
    # Attach focused candidate matrix
    focus = []
    pol_by = {p["stable_key"]: p for p in policy_rows}
    cont_by = {c["stable_key"]: c for c in contam_rows}
    sc_by = {s["stable_key"]: s for s in scorecards}
    for t in elig_traces:
        sk = t["stable_key"]
        focus.append(
            {
                "beam_id": t.get("beam_id"),
                "leader_id": t.get("leader_id"),
                "stable_key": sk,
                "current_t18_result": t.get("existing_t18_decision"),
                "current_rejection_reason": t.get("exact_r2_rejection_condition")
                or t.get("existing_ownership_reason"),
                "policy_A": (pol_by[sk].get("policy_results") or {}).get("A_CURRENT"),
                "policy_B": (pol_by[sk].get("policy_results") or {}).get("B_CHAIN_EVIDENCE"),
                "policy_C": (pol_by[sk].get("policy_results") or {}).get("C_CHAIN_ENDPOINT"),
                "policy_D": (pol_by[sk].get("policy_results") or {}).get("D_CHAIN_GEOMETRIC"),
                "policy_E": (pol_by[sk].get("policy_results") or {}).get("E_STRONG_COMBINED"),
                "evidence_that_changes_result": pol_by[sk].get(
                    "evidence_that_changes_result"
                ),
                "would_still_be_rejected_under_all": pol_by[sk].get(
                    "would_still_be_rejected_under_all"
                ),
                "neighbour_ambiguity": sc_by[sk].get("I_neighbour_ambiguity"),
                "inside_other_beam_envelope": sc_by[sk].get(
                    "H_inside_another_beam_envelope"
                ),
                "contamination_risk": cont_by[sk].get("cross_beam_contamination_risk"),
                "scorecard": sc_by[sk],
                "distance_mm": t.get("distance_tip_to_envelope"),
            }
        )

    impact = candidate_impact(
        eligible_traces=elig_traces,
        eligible_policies=elig_pols,
        eligible_contam=elig_cont,
    )
    root = build_root_cause(
        traces=traces,
        scorecards=scorecards,
        policies=policy_rows,
        comparison=comparison,
        contam_summary=contam_sum,
        impact=impact,
        eligible_keys=eligible_keys,
    )

    # Sort all outputs deterministically
    def _sk(r):
        return (
            str(r.get("beam_id") or ""),
            str(r.get("leader_id") or r.get("entity_id") or ""),
            str(r.get("stable_key") or ""),
        )

    traces = sorted(traces, key=_sk)
    scorecards = sorted(scorecards, key=_sk)
    policy_rows = sorted(policy_rows, key=_sk)
    focus = sorted(focus, key=_sk)

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "traces": traces,
        "scorecards": scorecards,
        "policy_rows": policy_rows,
        "decision_traces": sorted(decision_traces, key=_sk),
        "counterfactual_ownership": sorted(
            counterfactual_ownership,
            key=lambda r: (
                str(r.get("beam_id") or ""),
                str(r.get("leader_id") or ""),
                str(r.get("policy_used") or ""),
            ),
        ),
        "policy_comparison": comparison,
        "contamination": contam_sum,
        "excluded": excluded_sum,
        "focus_candidates": focus,
        "impact": impact,
        "root_cause": root,
        "leader_count": len(traces),
        "eligible_count": len(eligible_keys),
    }
