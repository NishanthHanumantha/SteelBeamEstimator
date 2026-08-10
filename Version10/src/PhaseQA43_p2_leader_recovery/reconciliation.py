"""
QA.4.3 reconciliation accounting.
MODEL_VERSION: 10.5.2
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


def build_reconciliation(
    *,
    original_dropped: int,
    leader_count: int,
    high_count: int,
    medium_count: int,
    low_count: int,
    unknown_count: int,
    audit_rows: List[Dict[str, Any]],
    recovery_candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    outcomes = Counter(r.get("recovery_outcome") for r in audit_rows)
    examined = len(audit_rows)
    eligible = sum(1 for r in audit_rows if r.get("recovery_eligible"))
    excluded = sum(
        1
        for r in audit_rows
        if r.get("recovery_outcome") in ("recovery_excluded", "diagnostic_only")
    )
    generated = sum(1 for r in audit_rows if r.get("recovery_candidate_generated"))
    added = sum(1 for r in audit_rows if r.get("recovery_candidate_added_to_pool"))
    already_prod = sum(
        1 for r in audit_rows if r.get("recovery_outcome") == "already_in_production_pool"
    )
    own_acc = sum(
        1 for r in audit_rows if r.get("recovery_outcome") == "ownership_accepted"
    )
    own_rej = sum(
        1 for r in audit_rows if r.get("recovery_outcome") == "ownership_rejected"
    )
    unresolved = sum(
        1 for r in audit_rows if r.get("recovery_outcome") == "unresolved"
    )
    accounted = sum(outcomes.values())
    engine_accepted = sum(
        1 for r in audit_rows if r.get("final_ownership_decision") == "ACCEPTED"
    )
    engine_rejected = sum(
        1 for r in audit_rows if r.get("final_ownership_decision") == "REJECTED"
    )
    changed = sum(1 for r in audit_rows if r.get("recovery_changed_decision"))
    nbr = sum(1 for r in audit_rows if r.get("neighbour_ambiguity"))
    inside = sum(1 for r in audit_rows if r.get("inside_other_beam_envelope"))
    far = sum(1 for r in audit_rows if r.get("spatial_relationship") == "FAR_OUTSIDE")

    return {
        "original_dropped": original_dropped,
        "leader_population": leader_count,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count,
        "unknown_count": unknown_count,
        "recovery_examined": examined,
        "recovery_eligible": eligible,
        "recovery_excluded": excluded,
        "recovery_candidate_generated": generated,
        "recovery_candidate_added": added,
        "already_in_production_pool": already_prod,
        "ownership_accepted": own_acc,
        "ownership_rejected": own_rej,
        "existing_engine_accepted": engine_accepted,
        "existing_engine_rejected": engine_rejected,
        "unresolved": unresolved,
        "ownership_decisions_changed": changed,
        "neighbour_ambiguity_count": nbr,
        "inside_other_beam_count": inside,
        "far_outside_count": far,
        "outcome_counts": dict(outcomes),
        "accounted": accounted,
        "examined_equals_accounted": accounted == examined,
        "leader_equals_examined": examined == leader_count,
        "recovery_candidates_len": len(recovery_candidates),
        "note": (
            "Zero newly-added candidates is valid when T18 already scored/rejected "
            "the leaders. QA.4.3 does not assign ownership."
        ),
    }
