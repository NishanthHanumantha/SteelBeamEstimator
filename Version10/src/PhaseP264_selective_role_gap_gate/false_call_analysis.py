"""Offline false-call analysis. Evaluation only."""
from __future__ import annotations

from typing import Any, Dict, List

from PhaseP263_longitudinal_aware_gate.false_call_analysis import (
    find_false_calls as p263_find,
)


def find_false_calls(
    *,
    decisions: List[Dict[str, Any]],
    gated_candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    out = p263_find(decisions=decisions, gated_candidates=gated_candidates)
    by = {(d.get("set_key"), d.get("beam_id")): d for d in decisions}
    for row in out:
        d = by.get((row.get("set_key"), row.get("beam_id"))) or {}
        row["role_gap_status"] = d.get("role_gap_status")
        row["role_gap_reason"] = d.get("role_gap_reason")
        row["production_coverage"] = d.get("longitudinal_coverage")
    return out


__all__ = ["find_false_calls"]
