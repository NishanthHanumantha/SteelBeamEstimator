"""Offline false-skip analysis. Evaluation only."""
from __future__ import annotations

from typing import Any, Dict, List

from PhaseP263_longitudinal_aware_gate.false_skip_analysis import (
    find_false_skips as p263_find,
)


def find_false_skips(
    *,
    decisions: List[Dict[str, Any]],
    frozen_candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    out = p263_find(decisions=decisions, frozen_candidates=frozen_candidates)
    by = {(d.get("set_key"), d.get("beam_id")): d for d in decisions}
    for row in out:
        d = by.get((row.get("set_key"), row.get("beam_id"))) or {}
        row["role_gap_status"] = d.get("role_gap_status")
        row["role_gap_reason"] = d.get("role_gap_reason")
    return out


__all__ = ["find_false_skips"]
