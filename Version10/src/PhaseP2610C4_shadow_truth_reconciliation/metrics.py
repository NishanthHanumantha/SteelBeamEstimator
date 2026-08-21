"""Aggregate calibration metrics against reconciled truth. Unresolved groups are not forced incorrect."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .config import (
    DECISION_DET,
    DECISION_INSUFFICIENT,
    DECISION_MIXED,
    DECISION_VISION,
    STATUS_AMBIGUOUS,
    STATUS_DET_CONFIRMED,
    STATUS_EQUIVALENT,
    STATUS_INSUFFICIENT,
    STATUS_VIS_CONFIRMED,
)


def aggregate_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = Counter(r.get("reconciliation_status") for r in records)
    vis_correct = vis_missing = vis_spurious = 0
    det_correct = det_missing = det_spurious = 0
    truth_n = 0
    scored = 0
    for r in records:
        if not r.get("truth_established"):
            continue
        scored += 1
        v = r.get("vision_vs_truth") or {}
        d = r.get("deterministic_vs_truth") or {}
        truth_n += int(v.get("expected_count") or 0)
        vis_correct += int(v.get("correct") or 0)
        vis_missing += int(v.get("missing") or 0)
        vis_spurious += int(v.get("spurious") or 0)
        det_correct += int(d.get("correct") or 0)
        det_missing += int(d.get("missing") or 0)
        det_spurious += int(d.get("spurious") or 0)
    vis_n = counts.get(STATUS_VIS_CONFIRMED, 0)
    det_n = counts.get(STATUS_DET_CONFIRMED, 0)
    eq_n = counts.get(STATUS_EQUIVALENT, 0)
    amb_n = counts.get(STATUS_AMBIGUOUS, 0)
    inf_n = counts.get(STATUS_INSUFFICIENT, 0)
    if vis_n == 0 and det_n == 0 and eq_n == 0:
        decision = DECISION_INSUFFICIENT
    elif vis_n > 0 and det_n > 0:
        decision = DECISION_MIXED
    elif vis_n > 0 and det_n == 0:
        decision = DECISION_VISION
    elif det_n > 0 and vis_n == 0:
        decision = DECISION_DET
    else:
        decision = DECISION_MIXED

    if decision == DECISION_VISION:
        recommendation = "A_SAMPLED_EXPANDED_SHADOW"
        recommendation_text = (
            "Proceed to a stratified sampled Vision shadow benchmark. "
            "Do not send the full LIMITED population. Keep Vision diagnostic-only until the sample is reviewed."
        )
    elif decision == DECISION_DET:
        recommendation = "D_DO_NOT_EXPAND"
        recommendation_text = "Do not expand Vision. Deterministic interpretation is the confirmed control signal."
    elif decision == DECISION_MIXED:
        recommendation = "B_RESTRICT_TO_AMBIGUITY_CLASSES"
        recommendation_text = "Restrict Vision to specific ambiguity classes. Keep diagnostic-only outside those classes."
    else:
        recommendation = "C_KEEP_DIAGNOSTIC_ONLY"
        recommendation_text = "Keep Vision diagnostic-only. Control evidence is insufficient to expand."

    return {
        "control_beam_count": len(records),
        "beams_reconciled": vis_n + det_n + eq_n,
        "beams_vision_confirmed": vis_n,
        "beams_deterministic_confirmed": det_n,
        "beams_both_equivalent": eq_n,
        "beams_ambiguous": amb_n,
        "beams_insufficient_evidence": inf_n,
        "beams_with_established_truth": scored,
        "reconciled_expected_group_count": truth_n,
        "deterministic_correct_group_count": det_correct,
        "deterministic_missing_group_count": det_missing,
        "deterministic_spurious_group_count": det_spurious,
        "vision_correct_group_count": vis_correct,
        "vision_missing_group_count": vis_missing,
        "vision_spurious_group_count": vis_spurious,
        "unresolved_excluded_from_forced_correctness": True,
        "decision": decision,
        "recommendation": recommendation,
        "recommendation_text": recommendation_text,
        "status_counts": dict(counts),
    }


__all__ = ["aggregate_metrics"]
