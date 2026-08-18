"""Counterfactual replay of frozen P2.6.1 Vision responses under the P2.6.3 gate."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .config import DECISION_CALL, DECISION_HOLD, DECISION_SKIP


def apply_gate_to_frozen(
    *,
    decisions: List[Dict[str, Any]],
    frozen_candidates: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    call_ids = set()
    skip_ids = set()
    hold_ids = set()
    by_key: Dict[Tuple[str, str], str] = {}
    for d in decisions:
        key = (str(d.get("set_key") or ""), str(d.get("beam_id") or ""))
        by_key[key] = str(d.get("decision"))
        bid = f"{d.get('set_key')}::{d.get('beam_id')}"
        if d.get("decision") == DECISION_CALL:
            call_ids.add(bid)
        elif d.get("decision") == DECISION_HOLD:
            hold_ids.add(bid)
        else:
            skip_ids.add(bid)

    gated: List[Dict[str, Any]] = []
    skipped_cands: List[Dict[str, Any]] = []
    for cand in frozen_candidates:
        key = (str(cand.get("set_key") or ""), str(cand.get("beam_id") or ""))
        decision = by_key.get(key, DECISION_SKIP)
        rec = dict(cand)
        rec["gate_decision"] = decision
        rec["replay_source"] = "FROZEN_P261_VISION"
        if decision == DECISION_CALL:
            gated.append(rec)
        else:
            skipped_cands.append(rec)

    summary = {
        "label": "Gated replay using frozen P2.6.1 Vision responses.",
        "not_a_new_vision_benchmark": True,
        "call_beams": len(call_ids),
        "skip_beams": len(skip_ids),
        "hold_beams": len(hold_ids),
        "gated_candidates": len(gated),
        "suppressed_candidates": len(skipped_cands),
    }
    return gated, summary


__all__ = ["apply_gate_to_frozen"]
