"""Offline false-call analysis. Evaluation only — not imported by the gate."""
from __future__ import annotations

from typing import Any, Dict, List

from .config import DECISION_CALL

GT_TRUE_RECOVERY = "TRUE_RECOVERY"


def find_false_calls(
    *,
    decisions: List[Dict[str, Any]],
    gated_candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    by_beam: Dict[str, List[Dict[str, Any]]] = {}
    for c in gated_candidates:
        key = f"{c.get('set_key')}::{c.get('beam_id')}"
        by_beam.setdefault(key, []).append(c)
    out: List[Dict[str, Any]] = []
    for d in decisions:
        if d.get("decision") != DECISION_CALL:
            continue
        key = f"{d.get('set_key')}::{d.get('beam_id')}"
        cands = by_beam.get(key) or []
        if any(c.get("gt_match_status") == GT_TRUE_RECOVERY for c in cands):
            continue
        statuses = [str(c.get("gt_match_status") or "") for c in cands]
        out.append(
            {
                "beam_id": d.get("beam_id"),
                "set_key": d.get("set_key"),
                "region_id": d.get("region_id"),
                "stratum": d.get("eval_stratum"),
                "gate_decision": d.get("decision"),
                "reason_codes": list(d.get("reason_codes") or []),
                "candidate_count": len(cands),
                "gt_status_counts": {
                    s: statuses.count(s) for s in sorted(set(statuses))
                },
            }
        )
    return out


__all__ = ["find_false_calls"]
