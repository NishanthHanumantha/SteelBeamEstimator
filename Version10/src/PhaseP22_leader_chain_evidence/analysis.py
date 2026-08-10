"""
P2.2 end-to-end analysis — reuses P2.1 evidence gathering; applies evaluator.
MODEL_VERSION: 10.5.4
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from PhaseP21_leader_tip_chain_analysis.analysis import run_analysis as run_p21_analysis
from PhaseQA31_pipeline_diagnostics.artefact_locator import PRIORITY_FOURTH_BEAMS

from .config import (
    DEFAULT_CONFIG,
    MODEL_VERSION,
    PHASE_ID,
    PRODUCTION_POLICY,
    EnhancedDecision,
    P22Config,
)
from .evaluator import LeaderChainEvidenceEvaluator
from .policies import POLICY_DEFS, policy_catalog


def _sk(row: Dict[str, Any]):
    return (
        str(row.get("beam_id") or ""),
        str(row.get("leader_id") or row.get("entity_id") or ""),
        str(row.get("stable_key") or ""),
    )


def run_analysis(
    *,
    population: Dict[str, Any],
    beam_ownership: Dict[str, Any],
    graph: Dict[str, Any],
    priority_beams: Sequence[str] = PRIORITY_FOURTH_BEAMS,
    config: P22Config = DEFAULT_CONFIG,
) -> Dict[str, Any]:
    """
    Gather evidence via P2.1 reconstruct/scorecard path, then apply P2.2 evaluator.

    Does not write BeamOwnership. Does not modify T18.
    """
    p21 = run_p21_analysis(
        population=population,
        beam_ownership=beam_ownership,
        graph=graph,
        priority_beams=priority_beams,
    )
    evaluator = LeaderChainEvidenceEvaluator(config)
    pop_by = {
        str(r.get("stable_key") or f"{r.get('beam_id')}::{r.get('entity_id')}"): r
        for r in (population.get("leaders") or [])
    }
    sc_by = {s["stable_key"]: s for s in (p21.get("scorecards") or [])}
    tr_by = {t["stable_key"]: t for t in (p21.get("traces") or [])}
    cont_by = {
        c["stable_key"]: c
        for c in ((p21.get("contamination") or {}).get("rows") or [])
    }

    decisions: List[Dict[str, Any]] = []
    for sk, sc in sorted(sc_by.items(), key=lambda kv: str(kv[0])):
        tr = tr_by.get(sk) or {}
        pop = pop_by.get(sk) or {}
        decision = evaluator.decide_leader(
            beam_id=str(sc.get("beam_id") or tr.get("beam_id") or ""),
            leader_id=str(sc.get("leader_id") or tr.get("leader_id") or ""),
            stable_key=sk,
            evidence=sc,
            current_t18_decision=str(tr.get("existing_t18_decision") or "REJECTED"),
            current_rejection_rule=tr.get("existing_rejected_rule")
            or tr.get("exact_r2_rejection_condition"),
            recovery_eligible=bool(pop.get("recovery_eligible")),
            recovery_potential=pop.get("recovery_potential"),
            evidence_details={
                "distance_tip_to_envelope_mm": tr.get("distance_tip_to_envelope"),
                "distance_tip_to_support_mm": tr.get("distance_tip_to_support"),
                "bar_distance_mm": tr.get("bar_distance"),
                "J_distance_from_envelope_mm": sc.get("J_distance_from_envelope_mm"),
                "contamination_risk": (cont_by.get(sk) or {}).get(
                    "cross_beam_contamination_risk"
                ),
            },
        )
        decisions.append(decision)

    decisions = sorted(decisions, key=_sk)

    # Policy comparison counts (diagnostic A–E)
    counts = {p: 0 for p in POLICY_DEFS}
    eligible_counts = {p: 0 for p in POLICY_DEFS}
    for d in decisions:
        pr = d.get("policy_results") or {}
        for p, v in pr.items():
            if v:
                counts[p] = counts.get(p, 0) + 1
                if d.get("recovery_eligible"):
                    eligible_counts[p] = eligible_counts.get(p, 0) + 1

    accept_candidates = [
        d
        for d in decisions
        if d.get("enhanced_decision") == EnhancedDecision.ACCEPT_CANDIDATE.value
    ]
    reject_contam = [
        d
        for d in decisions
        if d.get("neighbour_ambiguity") or d.get("inside_other_beam_envelope")
    ]
    reject_contam_still_rejected = [
        d
        for d in reject_contam
        if d.get("enhanced_decision") != EnhancedDecision.ACCEPT_CANDIDATE.value
    ]

    comparison = {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "policy_definitions": POLICY_DEFS,
        "accepted_count_all_23": counts,
        "accepted_count_among_5_eligible": eligible_counts,
        "production_policy": PRODUCTION_POLICY,
        "production_candidate_count": len(accept_candidates),
        "note": (
            "Diagnostic / production-candidate counts only — "
            "BeamOwnership not written in DIAGNOSTIC_ONLY mode"
        ),
    }

    summary = {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "label": config.label,
        "production_gate": config.production_gate.value,
        "production_policy": PRODUCTION_POLICY,
        "leader_count": len(decisions),
        "eligible_count": int(population.get("eligible_count") or 0),
        "policy_e_accept_all": counts.get(PRODUCTION_POLICY, 0),
        "policy_e_accept_eligible": eligible_counts.get(PRODUCTION_POLICY, 0),
        "production_candidate_count": len(accept_candidates),
        "production_candidate_keys": [d["stable_key"] for d in accept_candidates],
        "contamination_cases": len(reject_contam),
        "contamination_cases_still_rejected": len(reject_contam_still_rejected),
        "beam_ownership_written": False,
        "t18_modified": False,
        "r2_leader_tip_modified": False,
        "envelope_modified": False,
        "ready_for_controlled_production_gate": False,  # set by validator
        "status": "PENDING_VALIDATION",
    }

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "label": config.label,
        "production_gate": config.production_gate.value,
        "decisions": decisions,
        "accept_candidates": accept_candidates,
        "policy_comparison": comparison,
        "policy_catalog": policy_catalog(),
        "summary": summary,
        "p21_evidence": {
            "traces": p21.get("traces"),
            "scorecards": p21.get("scorecards"),
            "focus_candidates": p21.get("focus_candidates"),
            "contamination": p21.get("contamination"),
        },
        "leader_count": len(decisions),
        "eligible_count": int(population.get("eligible_count") or 0),
        "beam_ownership_written": False,
    }
