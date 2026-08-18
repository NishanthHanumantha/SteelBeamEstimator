"""Offline evaluator. Not used by P2.6.4 routing."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PhaseP264_selective_role_gap_gate.false_call_analysis import find_false_calls
from PhaseP264_selective_role_gap_gate.false_skip_analysis import find_false_skips

from .config import CLEARANCE_RATIO, REPEAT_SEPARATION_RATIO
from .context_classifier import classify_spatial_context
from .control_cases import build_control_table
from .metrics import classify_gate, compute_metrics


def evaluate_replay(
    *,
    decisions: List[Dict[str, Any]],
    baseline_candidates: List[Dict[str, Any]],
    gated_candidates: List[Dict[str, Any]],
    firewall_ok: bool = True,
    leakage_ok: bool = True,
    fingerprints_ok: bool = True,
    hypothetical_metrics: Optional[Dict[str, Any]] = None,
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
    controls = build_control_table(decisions=decisions, frozen_candidates=baseline_candidates)
    recommendation = classify_gate(
        metrics,
        firewall_ok=firewall_ok,
        leakage_ok=leakage_ok,
        fingerprints_ok=fingerprints_ok,
        hypothetical=hypothetical_metrics,
    )
    return {
        "metrics": metrics,
        "false_skips": false_skips,
        "false_calls": false_calls,
        "control_cases": controls,
        "recommendation": recommendation,
    }


def sensitivity_analysis(decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
    ratios = (0.10, 0.15, 0.20)
    out: Dict[str, Any] = {
        "clearance_ratio_default": CLEARANCE_RATIO,
        "repeat_ratio_default": REPEAT_SEPARATION_RATIO,
        "method": "recompute tip-layer votes from stored zone distances; classifier is categorical",
    }
    table = []
    for cr in ratios:
        counts = {
            "CONTEXT_SUPPORTS_CALL": 0,
            "CONTEXT_SUPPORTS_SKIP": 0,
            "CONTEXT_AMBIGUOUS": 0,
            "CONTEXT_INSUFFICIENT": 0,
        }
        for d in decisions:
            spat = dict(d.get("spatial_features") or {})
            depth = float(spat.get("depth_mm") or 600.0)
            clearance = cr * depth
            votes = []
            for row in d.get("per_annotation_spatial") or []:
                dt = row.get("dist_tip_top_zone")
                db = row.get("dist_tip_bottom_zone")
                if dt is None or db is None:
                    continue
                if row.get("tip_in_top_zone") and db >= clearance:
                    votes.append("TOP")
                elif row.get("tip_in_bottom_zone") and dt >= clearance:
                    votes.append("BOTTOM")
                elif row.get("tip_in_top_zone") or row.get("tip_in_bottom_zone"):
                    votes.append("BOUNDARY")
                elif dt < db:
                    votes.append("NEAR_TOP")
                else:
                    votes.append("NEAR_BOTTOM")
            spat["tip_layer_votes"] = votes
            ctx = classify_spatial_context(
                spatial=spat,
                production_features=d.get("production_features") or {},
                longitudinal_coverage=d.get("longitudinal_coverage"),
                clearance_ratio=cr,
            )
            counts[ctx["context_status"]] = counts.get(ctx["context_status"], 0) + 1
        table.append({"clearance_ratio": cr, **counts})
    out["by_clearance_ratio"] = table
    keys = [(r["CONTEXT_SUPPORTS_CALL"], r["CONTEXT_SUPPORTS_SKIP"]) for r in table]
    out["stable"] = len(set(keys)) == 1
    return out


__all__ = ["evaluate_replay", "sensitivity_analysis"]
