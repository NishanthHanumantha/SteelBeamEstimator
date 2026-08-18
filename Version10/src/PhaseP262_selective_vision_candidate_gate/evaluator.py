"""Offline evaluator wrapping false-skip / false-call detection. Not used by the gate."""
from __future__ import annotations

from typing import Any, Dict, List

from .false_call_analysis import find_false_calls
from .false_skip_analysis import find_false_skips
from .metrics import classify_gate, compute_metrics


def evaluate_replay(
    *,
    decisions: List[Dict[str, Any]],
    baseline_candidates: List[Dict[str, Any]],
    gated_candidates: List[Dict[str, Any]],
    firewall_ok: bool = True,
    review_high: bool = False,
) -> Dict[str, Any]:
    false_skips = find_false_skips(decisions=decisions, frozen_candidates=baseline_candidates)
    false_calls = find_false_calls(decisions=decisions, gated_candidates=gated_candidates)
    metrics = compute_metrics(
        decisions=decisions,
        baseline_candidates=baseline_candidates,
        gated_candidates=gated_candidates,
        false_skips=false_skips,
        false_calls=false_calls,
    )
    recommendation = classify_gate(metrics, firewall_ok=firewall_ok, review_high=review_high)
    return {
        "metrics": metrics,
        "false_skips": false_skips,
        "false_calls": false_calls,
        "recommendation": recommendation,
    }


__all__ = ["evaluate_replay"]
