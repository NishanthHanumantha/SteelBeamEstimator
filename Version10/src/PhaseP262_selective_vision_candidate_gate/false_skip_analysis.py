"""Offline false-skip analysis. Evaluation only — not imported by the gate."""
from __future__ import annotations

from typing import Any, Dict, List

from .config import DECISION_CALL

GT_TRUE_RECOVERY = "TRUE_RECOVERY"


def find_false_skips(
    *,
    decisions: List[Dict[str, Any]],
    frozen_candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rec_by_beam: Dict[str, List[Dict[str, Any]]] = {}
    for c in frozen_candidates:
        key = f"{c.get('set_key')}::{c.get('beam_id')}"
        rec_by_beam.setdefault(key, []).append(c)
    out: List[Dict[str, Any]] = []
    for d in decisions:
        if d.get("decision") == DECISION_CALL:
            continue
        key = f"{d.get('set_key')}::{d.get('beam_id')}"
        recs = [
            c
            for c in rec_by_beam.get(key) or []
            if c.get("gt_match_status") == GT_TRUE_RECOVERY
        ]
        if not recs:
            continue
        for c in recs:
            out.append(
                {
                    "beam_id": d.get("beam_id"),
                    "set_key": d.get("set_key"),
                    "region_id": d.get("region_id"),
                    "stratum": d.get("eval_stratum"),
                    "gate_decision": d.get("decision"),
                    "why_gate_skipped": list(d.get("reason_codes") or []),
                    "production_features": d.get("production_features") or {},
                    "annotation": c.get("annotation_text"),
                    "candidate_class": c.get("candidate_type"),
                    "candidate_id": c.get("candidate_id"),
                    "gt_recovery": c.get("gt_match_status"),
                    "deterministic_match_status": c.get("deterministic_match_status"),
                }
            )
    return out


__all__ = ["find_false_skips"]
