"""Offline false-skip analysis. Evaluation only."""
from __future__ import annotations

from typing import Any, Dict, List

from .config import DECISION_CALL

GT_TRUE_RECOVERY = "TRUE_RECOVERY"


def _ann_cov(decision: Dict[str, Any], text: Any) -> Dict[str, Any]:
    want = "".join(str(text or "").split()).upper()
    for row in decision.get("per_annotation_coverage") or []:
        if "".join(str(row.get("normalized_text") or row.get("text") or "").split()).upper() == want:
            return row
    rows = decision.get("per_annotation_coverage") or []
    return rows[0] if rows else {}


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
        for c in recs:
            cov = _ann_cov(d, c.get("annotation_text"))
            out.append(
                {
                    "beam_id": d.get("beam_id"),
                    "set_key": d.get("set_key"),
                    "region_id": d.get("region_id"),
                    "stratum": d.get("eval_stratum"),
                    "gate_decision": d.get("decision"),
                    "why_gate_skipped": list(d.get("reason_codes") or []),
                    "production_features": d.get("production_features") or {},
                    "production_coverage": d.get("longitudinal_coverage"),
                    "coverage_conditions": d.get("coverage_conditions") or [],
                    "annotation": c.get("annotation_text"),
                    "role": cov.get("role") or c.get("role"),
                    "diameter": cov.get("diameter_mm") or c.get("diameter_mm"),
                    "quantity": cov.get("quantity") if cov.get("quantity") is not None else c.get("quantity"),
                    "candidate_class": c.get("candidate_type"),
                    "candidate_id": c.get("candidate_id"),
                    "gt_recovery": c.get("gt_match_status"),
                    "deterministic_match_status": c.get("deterministic_match_status"),
                }
            )
    return out


__all__ = ["find_false_skips"]
