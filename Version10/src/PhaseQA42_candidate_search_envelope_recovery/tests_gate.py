"""
Explicit QA.4.2 test cases TEST 01–12.
MODEL_VERSION: 10.5.1
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def run_test_cases(
    *,
    audit_rows: List[Dict[str, Any]],
    diagnostic_rows: List[Dict[str, Any]],
    populations: Dict[str, Any],
    contamination: Dict[str, Any],
    determinism: Optional[Dict[str, Any]],
    owned_elsewhere_ids: set,
) -> Dict[str, Any]:
    tests = []

    def add(tid: str, name: str, ok: bool, detail: Any = None) -> None:
        tests.append({"test_id": tid, "name": name, "pass": bool(ok), "detail": detail})

    # TEST 01 — Boundary envelope case exists and is examined
    boundary = [
        r for r in audit_rows if r.get("spatial_relationship") == "BOUNDARY"
    ]
    add("TEST_01", "Boundary envelope case", len(boundary) > 0, len(boundary))

    # TEST 02 — Near-outside HIGH case
    near = [
        r for r in audit_rows if r.get("spatial_relationship") == "NEAR_OUTSIDE"
    ]
    add("TEST_02", "Near-outside HIGH case", len(near) > 0, len(near))

    # TEST 03 — Target-beam-context HIGH
    tgt = [r for r in audit_rows if r.get("target_beam_context")]
    add("TEST_03", "Target-beam-context HIGH case", len(tgt) > 0, len(tgt))

    # TEST 04 — Neighbour ambiguity: must not generate new pool adds
    nbr_diag = [r for r in diagnostic_rows if r.get("neighbour_ambiguity")]
    nbr_audit_added = [
        r
        for r in audit_rows
        if r.get("neighbour_ambiguity") and r.get("recovery_candidate_added_to_pool")
    ]
    add(
        "TEST_04",
        "Neighbour ambiguity case not newly added",
        len(nbr_audit_added) == 0,
        {"diagnostic_nbr": len(nbr_diag), "illegally_added": len(nbr_audit_added)},
    )

    # TEST 05 — Inside-other-beam-envelope not newly added
    inside_added = [
        r
        for r in audit_rows
        if r.get("inside_other_beam_envelope")
        and r.get("recovery_candidate_added_to_pool")
    ]
    add(
        "TEST_05",
        "Inside-other-beam-envelope case",
        len(inside_added) == 0,
        len(inside_added),
    )

    # TEST 06 — Far-outside LOW remains diagnostic-only
    far_low = [
        r
        for r in diagnostic_rows
        if r.get("recovery_potential") == "LOW"
        and r.get("spatial_relationship") == "FAR_OUTSIDE"
    ]
    far_in_recovery_added = [
        r
        for r in audit_rows
        if r.get("spatial_relationship") == "FAR_OUTSIDE"
        and r.get("recovery_candidate_added_to_pool")
    ]
    add(
        "TEST_06",
        "Far-outside LOW case diagnostic only",
        len(far_low) > 0 and len(far_in_recovery_added) == 0,
        {"far_low": len(far_low), "illegally_added": len(far_in_recovery_added)},
    )

    # TEST 07 — Owned-elsewhere not recovered
    oe_recovered = [
        r
        for r in audit_rows
        if r.get("entity_id") in owned_elsewhere_ids
        and r.get("recovery_candidate_generated")
    ]
    add(
        "TEST_07",
        "Owned-elsewhere entity not recovered",
        len(oe_recovered) == 0,
        len(oe_recovered),
    )

    # TEST 08 — Duplicate stable keys
    add(
        "TEST_08",
        "Duplicate stable key",
        (contamination.get("duplicate_stable_key_count") or 0) == 0,
        contamination.get("duplicate_stable_key_count"),
    )

    # TEST 09 — Already present in production pool handled via dedupe
    already = [
        r for r in audit_rows if r.get("recovery_outcome") == "already_in_production_pool"
    ]
    add(
        "TEST_09",
        "Entity already present in production candidate pool",
        len(already) > 0
        and all(not r.get("recovery_candidate_added_to_pool") for r in already),
        len(already),
    )

    # TEST 10 / 11 — Fifth / Sixth
    add(
        "TEST_10",
        "Fifth Set entity",
        int(populations.get("fifth_set_recovery_population") or 0) == 0,
        populations.get("fifth_set_recovery_population"),
    )
    add(
        "TEST_11",
        "Sixth Set entity",
        int(populations.get("sixth_set_recovery_population") or 0) == 0,
        populations.get("sixth_set_recovery_population"),
    )

    # TEST 12 — Determinism
    det_ok = (determinism or {}).get("determinism_status") == "PASS"
    add("TEST_12", "Repeated identical run for determinism", det_ok, determinism)

    return {
        "all_pass": all(t["pass"] for t in tests),
        "tests": tests,
        "failed": [t["test_id"] for t in tests if not t["pass"]],
    }
