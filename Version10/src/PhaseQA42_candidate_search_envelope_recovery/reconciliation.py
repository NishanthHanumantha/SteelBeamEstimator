"""
Before/after accounting for QA.4.2 recovery.
MODEL_VERSION: 10.5.1
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


def build_reconciliation(
    *,
    original_dropped: int,
    envelope_count: int,
    high_count: int,
    medium_count: int,
    low_count: int,
    audit_rows: List[Dict[str, Any]],
    recovery_candidates: List[Dict[str, Any]],
    diagnostic_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    outcomes = Counter(r.get("recovery_outcome") for r in audit_rows)
    examined = len(audit_rows)
    eligible = sum(1 for r in audit_rows if r.get("recovery_eligible"))
    candidate_generated = sum(
        1 for r in audit_rows if r.get("recovery_candidate_generated")
    )
    candidate_added = sum(
        1 for r in audit_rows if r.get("recovery_candidate_added_to_pool")
    )
    already = sum(
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
    recovery_excluded = sum(
        1
        for r in audit_rows
        if str(r.get("recovery_outcome") or "").startswith("recovery_excluded")
    )
    # Every examined entity exactly once
    accounted = (
        outcomes.get("recovery_excluded", 0)
        + outcomes.get("recovery_excluded_contamination", 0)
        + outcomes.get("already_in_production_pool", 0)
        + outcomes.get("ownership_accepted", 0)
        + outcomes.get("ownership_rejected", 0)
        + outcomes.get("unresolved", 0)
    )

    # Engine accepted includes already-present confirmations
    engine_accepted = sum(
        1
        for r in audit_rows
        if r.get("final_ownership_decision") == "ACCEPTED"
        or r.get("recovery_outcome") == "already_in_production_pool"
    )
    engine_rejected = sum(
        1 for r in audit_rows if r.get("final_ownership_decision") == "REJECTED"
    )
    changed = sum(1 for r in audit_rows if r.get("recovery_changed_decision"))

    return {
        "original_dropped": original_dropped,
        "envelope_population": envelope_count,
        "high_potential_population": high_count,
        "medium_population": medium_count,
        "low_population": low_count,
        "recovery_examined": examined,
        "recovery_eligible": eligible,
        "recovery_excluded": recovery_excluded,
        "recovery_candidate_generated": candidate_generated,
        "recovery_candidate_added": candidate_added,
        "already_in_production_pool": already,
        "ownership_rejected": own_rej,
        "ownership_accepted": own_acc,
        "existing_engine_accepted": engine_accepted,
        "existing_engine_rejected": engine_rejected,
        "unresolved": unresolved,
        "ownership_decisions_changed": changed,
        "diagnostic_medium_low_count": len(diagnostic_rows),
        "outcome_counts": dict(outcomes),
        "accounted": accounted,
        "examined_equals_accounted": accounted == examined,
        "high_equals_examined": examined == high_count,
        "recovery_candidates_len": len(recovery_candidates),
        "note": (
            "already_in_production_pool means entity was eligible but deduped against "
            "existing T18 accepted_node_ids; production envelope unchanged; "
            "QA.4.2 did not assign ownership."
        ),
    }
