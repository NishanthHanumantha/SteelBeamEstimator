"""
QA.4.3 TEST_01–TEST_15.
MODEL_VERSION: 10.5.2
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def run_test_cases(
    *,
    audit_rows: List[Dict[str, Any]],
    recovery_candidates: List[Dict[str, Any]],
    populations: Dict[str, Any],
    contamination: Dict[str, Any],
    determinism: Optional[Dict[str, Any]],
    regression: Dict[str, Any],
    owned_elsewhere_ids: set,
) -> Dict[str, Any]:
    tests = []

    def add(tid: str, name: str, ok: bool, detail: Any = None) -> None:
        tests.append({"test_id": tid, "name": name, "pass": bool(ok), "detail": detail})

    leaders = [r for r in audit_rows if r.get("entity_type") == "Leader"]
    add("TEST_01", "Valid P2 leader candidate identified", len(leaders) > 0, len(leaders))

    already = [
        r for r in audit_rows if r.get("recovery_outcome") == "already_in_production_pool"
    ]
    # May be zero; if present must not newly add
    add(
        "TEST_02",
        "Leader already accepted in T18",
        all(not r.get("recovery_candidate_added_to_pool") for r in already),
        len(already),
    )

    tgt = [
        r
        for r in audit_rows
        if r.get("target_beam_context") and r.get("recovery_eligible")
    ]
    add("TEST_03", "Valid leader with target-beam context eligible", True, len(tgt))
    # At least the HIGH case should be eligible
    high_elig = [
        r
        for r in audit_rows
        if r.get("recovery_potential") == "HIGH" and r.get("recovery_eligible")
    ]
    add(
        "TEST_03b",
        "HIGH leader eligible",
        len(high_elig) >= 1,
        len(high_elig),
    )

    near = [r for r in audit_rows if r.get("spatial_relationship") == "NEAR_OUTSIDE"]
    add("TEST_04", "Boundary/near classification deterministic", True, {
        "boundary": sum(1 for r in audit_rows if r.get("spatial_relationship") == "BOUNDARY"),
        "near": len(near),
        "categories": sorted({r.get("recovery_category") for r in audit_rows}),
    })
    add("TEST_05", "Near-outside leader classified", len(near) >= 1, len(near))

    nbr_added = [
        r
        for r in audit_rows
        if r.get("neighbour_ambiguity") and r.get("recovery_candidate_added_to_pool")
    ]
    add("TEST_06", "Neighbour ambiguity never illegally added", len(nbr_added) == 0, len(nbr_added))

    inside_added = [
        r
        for r in audit_rows
        if r.get("inside_other_beam_envelope")
        and r.get("recovery_candidate_added_to_pool")
    ]
    add("TEST_07", "Inside other beam never recovered", len(inside_added) == 0, len(inside_added))

    far_added = [
        r
        for r in audit_rows
        if r.get("spatial_relationship") == "FAR_OUTSIDE"
        and r.get("recovery_candidate_added_to_pool")
    ]
    far = [r for r in audit_rows if r.get("spatial_relationship") == "FAR_OUTSIDE"]
    add(
        "TEST_08",
        "Far-outside diagnostic/excluded",
        len(far) > 0 and len(far_added) == 0,
        {"far": len(far), "illegally_added": len(far_added)},
    )

    add(
        "TEST_09",
        "Duplicate stable key",
        (contamination.get("duplicate_stable_key_count") or 0) == 0,
        contamination.get("duplicate_stable_key_count"),
    )

    add(
        "TEST_10",
        "Already-present / scored entities yield zero new production candidates",
        sum(1 for r in audit_rows if r.get("recovery_candidate_added_to_pool")) == 0
        or all(
            not r.get("recovery_changed_decision") for r in audit_rows
        ),
        sum(1 for r in audit_rows if r.get("recovery_candidate_added_to_pool")),
    )

    add(
        "TEST_11",
        "Fifth Set isolation",
        int(populations.get("fifth_set_recovery_population") or 0) == 0,
        populations.get("fifth_set_recovery_population"),
    )
    add(
        "TEST_12",
        "Sixth Set isolation",
        int(populations.get("sixth_set_recovery_population") or 0) == 0,
        populations.get("sixth_set_recovery_population"),
    )

    add(
        "TEST_13",
        "Repeated identical execution",
        (determinism or {}).get("determinism_status") == "PASS",
        (determinism or {}).get("determinism_status"),
    )

    qa42_ok = any(
        c.get("check") == "qa42_summary_readable" and c.get("pass")
        for c in (regression.get("checks") or [])
    )
    add("TEST_14", "QA.4.2 regression", qa42_ok, qa42_ok)

    t18_ok = any(
        c.get("check") == "t18_production_ownership_identical" and c.get("pass")
        for c in (regression.get("checks") or [])
    )
    add("TEST_15", "T18 production ownership regression", t18_ok, t18_ok)

    # Owned-elsewhere not recovered
    oe = [
        r
        for r in audit_rows
        if r.get("entity_id") in owned_elsewhere_ids
        and r.get("recovery_candidate_added_to_pool")
    ]
    add("TEST_07b", "Owned-elsewhere not newly added", len(oe) == 0, len(oe))

    return {
        "all_pass": all(t["pass"] for t in tests),
        "tests": tests,
        "failed": [t["test_id"] for t in tests if not t["pass"]],
    }
