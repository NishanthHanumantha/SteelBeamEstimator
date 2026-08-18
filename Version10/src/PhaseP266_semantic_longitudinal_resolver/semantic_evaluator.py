"""Offline evaluator. Not used by P2.6.4 / P2.6.5 routing."""
from __future__ import annotations

from typing import Any, Dict, List

from PhaseP264_selective_role_gap_gate.false_call_analysis import find_false_calls
from PhaseP264_selective_role_gap_gate.false_skip_analysis import find_false_skips
from PhaseP264_selective_role_gap_gate.replay_runner import apply_gate_to_frozen

from .config import COVER_FULL, COVER_LAYER, DET_CONFLICT, DECISION_SKIP
from .control_cases import build_control_table
from .frozen_sample import candidates_for_beam
from .semantic_metrics import (
    classify_gate,
    compute_semantic_metrics,
    observed_vs_hypothetical_decisions,
)


def is_semantic_target(decision: Dict[str, Any], frozen_candidates: List[Dict[str, Any]]) -> bool:
    if decision.get("longitudinal_coverage") == COVER_LAYER:
        return True
    if decision.get("longitudinal_coverage") != COVER_FULL:
        return False
    if decision.get("decision") != DECISION_SKIP and decision.get("observed_decision") != DECISION_SKIP:
        return False
    cands = candidates_for_beam(
        frozen_candidates, str(decision.get("set_key") or ""), str(decision.get("beam_id") or "")
    )
    return any(
        "LONGITUDINAL" in str(c.get("candidate_type") or "").upper()
        and c.get("deterministic_match_status") == DET_CONFLICT
        for c in cands
    )


def evaluate_replay(
    *,
    p265_decisions: List[Dict[str, Any]],
    target_records: List[Dict[str, Any]],
    frozen_candidates: List[Dict[str, Any]],
    replay_summary: Dict[str, Any],
    firewall_ok: bool = True,
    leakage_ok: bool = True,
    fingerprints_ok: bool = True,
) -> Dict[str, Any]:
    observed_gated, _ = apply_gate_to_frozen(
        decisions=p265_decisions, frozen_candidates=frozen_candidates
    )
    observed_fs = find_false_skips(decisions=p265_decisions, frozen_candidates=frozen_candidates)
    observed_fc = find_false_calls(decisions=p265_decisions, gated_candidates=observed_gated)
    from PhaseP264_selective_role_gap_gate.metrics import compute_metrics as p264_metrics

    observed_metrics = p264_metrics(
        decisions=p265_decisions,
        baseline_candidates=frozen_candidates,
        gated_candidates=observed_gated,
        false_skips=observed_fs,
        false_calls=observed_fc,
    )
    hypo_decisions = observed_vs_hypothetical_decisions(
        p265_decisions=p265_decisions, target_records=target_records
    )
    hypo_gated, _ = apply_gate_to_frozen(
        decisions=hypo_decisions, frozen_candidates=frozen_candidates
    )
    hypo_fs = find_false_skips(decisions=hypo_decisions, frozen_candidates=frozen_candidates)
    hypo_fc = find_false_calls(decisions=hypo_decisions, gated_candidates=hypo_gated)
    hypo_metrics = p264_metrics(
        decisions=hypo_decisions,
        baseline_candidates=frozen_candidates,
        gated_candidates=hypo_gated,
        false_skips=hypo_fs,
        false_calls=hypo_fc,
    )
    controls = build_control_table(records=target_records, frozen_candidates=frozen_candidates)
    # Controls not in the 18+diagnostic set still need P265 fields; merge from full sample.
    if any(not r.get("in_sample") for r in controls):
        merged = list(target_records)
        seen = {(r.get("set_key"), r.get("beam_id")) for r in merged}
        for d in p265_decisions:
            key = (d.get("set_key"), d.get("beam_id"))
            if key in seen:
                continue
            merged.append(d)
        controls = build_control_table(records=merged, frozen_candidates=frozen_candidates)
    metrics = compute_semantic_metrics(
        target_records=target_records,
        controls=controls,
        observed_metrics=observed_metrics,
        hypothetical_metrics=hypo_metrics,
        false_skips=hypo_fs,
        false_calls=hypo_fc,
        replay_summary=replay_summary,
    )
    recommendation = classify_gate(
        metrics,
        firewall_ok=firewall_ok,
        leakage_ok=leakage_ok,
        fingerprints_ok=fingerprints_ok,
    )
    return {
        "metrics": metrics,
        "observed_metrics": observed_metrics,
        "hypothetical_metrics": hypo_metrics,
        "false_skips": hypo_fs,
        "false_calls": hypo_fc,
        "observed_false_skips": observed_fs,
        "control_cases": controls,
        "recommendation": recommendation,
        "hypothetical_decisions": hypo_decisions,
    }


__all__ = ["evaluate_replay", "is_semantic_target"]
