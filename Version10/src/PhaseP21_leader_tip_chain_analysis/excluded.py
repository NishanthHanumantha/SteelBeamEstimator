"""
Classify the 18 non-eligible leaders (why they should remain excluded).
MODEL_VERSION: 10.5.3
"""
from __future__ import annotations

from typing import Any, Dict, List

from .config import MODEL_VERSION, PHASE_ID


def classify_excluded(
    trace: Dict[str, Any], scorecard: Dict[str, Any], policy_row: Dict[str, Any]
) -> Dict[str, Any]:
    spatial = trace.get("spatial_relationship")
    nbr = scorecard.get("I_neighbour_ambiguity")
    inside = scorecard.get("H_inside_another_beam_envelope")
    pot = trace.get("recovery_potential")
    would_any = bool((policy_row.get("policies_that_would_accept") or []))
    # Exclude Policy A from "would accept under relaxation"
    would_relax = any(
        p != "A_CURRENT" for p in (policy_row.get("policies_that_would_accept") or [])
    )

    if nbr:
        cls = "NEIGHBOUR_AMBIGUITY"
    elif inside:
        cls = "NEIGHBOUR_AMBIGUITY"  # treated as neighbour risk
        if scorecard.get("H_inside_another_beam_envelope"):
            cls = "LIKELY_FALSE_RECOVERY"
    elif spatial == "FAR_OUTSIDE":
        cls = "FAR_OUTSIDE"
    elif would_relax and not nbr and not inside:
        cls = "LEGITIMATE_RECOVERY_SIGNAL"
    elif pot in ("LOW", "UNKNOWN") and not would_relax:
        cls = "INSUFFICIENT_EVIDENCE"
    elif not scorecard.get("A_chain_continuity"):
        cls = "OTHER"  # broken chain
    else:
        cls = "INSUFFICIENT_EVIDENCE"

    # Refine inside-other
    if inside:
        cls = "LIKELY_FALSE_RECOVERY"

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "beam_id": trace.get("beam_id"),
        "leader_id": trace.get("leader_id"),
        "stable_key": trace.get("stable_key"),
        "exclusion_class": cls,
        "spatial_relationship": spatial,
        "recovery_potential": pot,
        "would_accept_under_any_relaxation_policy": would_relax,
        "neighbour_ambiguity": nbr,
        "inside_other_beam_envelope": inside,
        "should_remain_excluded": cls
        in ("NEIGHBOUR_AMBIGUITY", "FAR_OUTSIDE", "LIKELY_FALSE_RECOVERY", "INSUFFICIENT_EVIDENCE", "OTHER")
        or not would_relax,
    }


def summarize_excluded(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    from collections import Counter

    return {
        "phase_id": PHASE_ID,
        "count": len(rows),
        "class_counts": dict(Counter(r.get("exclusion_class") for r in rows)),
        "rows": rows,
    }
