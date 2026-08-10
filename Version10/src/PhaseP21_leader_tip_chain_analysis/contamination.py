"""
Counterfactual contamination assessment (diagnostic only).
MODEL_VERSION: 10.5.3
"""
from __future__ import annotations

from typing import Any, Dict, List

from .config import MODEL_VERSION, PHASE_ID


def assess_contamination(trace: Dict[str, Any], scorecard: Dict[str, Any]) -> Dict[str, Any]:
    nbr = bool(scorecard.get("I_neighbour_ambiguity"))
    inside = bool(scorecard.get("H_inside_another_beam_envelope"))
    points = bool(scorecard.get("E_points_toward_target_beam"))
    ctx = bool(scorecard.get("C_target_beam_context"))
    bar = bool(scorecard.get("B_leader_to_bar_proximity"))
    other_ids = list(trace.get("inside_other_beam_ids") or [])
    nearest = trace.get("nearest_competing_beam")
    d_comp = trace.get("distance_to_competing_beam")
    d_tgt = trace.get("distance_tip_to_envelope")

    stronger_other = False
    if d_comp is not None and d_tgt is not None and float(d_comp) + 1e-6 < float(d_tgt):
        stronger_other = True

    if inside or other_ids:
        risk = "UNSAFE"
        reason = "inside_other_beam_envelope"
    elif nbr or stronger_other:
        risk = "AMBIGUOUS"
        reason = "neighbour_ambiguity_or_closer_to_competitor"
    elif ctx and (points or bar) and not nbr and not inside:
        risk = "SAFE"
        reason = "target_context_without_neighbour_conflict"
    elif not ctx:
        risk = "AMBIGUOUS"
        reason = "missing_target_beam_context"
    else:
        risk = "AMBIGUOUS"
        reason = "incomplete_contamination_evidence"

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "beam_id": trace.get("beam_id"),
        "leader_id": trace.get("leader_id"),
        "stable_key": trace.get("stable_key"),
        "target_beam": trace.get("target_beam"),
        "nearest_competing_beam": nearest,
        "distance_to_competing_beam": d_comp,
        "distance_to_target_envelope": d_tgt,
        "inside_other_beam_envelope": inside,
        "inside_other_beam_ids": other_ids,
        "other_beam_stronger_geometric_evidence": stronger_other,
        "leader_points_toward_target_beam": points,
        "leader_chain_connects_to_target_bar": bar and bool(trace.get("associated_bar")),
        "annotation_target_is_target_beam": bool(trace.get("target_annotation")),
        "cross_beam_contamination_risk": risk,
        "risk_reason": reason,
    }


def contamination_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    from collections import Counter

    c = Counter(r.get("cross_beam_contamination_risk") for r in rows)
    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "counts": dict(c),
        "safe_count": c.get("SAFE", 0),
        "ambiguous_count": c.get("AMBIGUOUS", 0),
        "unsafe_count": c.get("UNSAFE", 0),
        "rows": rows,
    }
