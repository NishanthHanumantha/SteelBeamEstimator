"""
QA.4.2 validation gates.
MODEL_VERSION: 10.5.1
"""
from __future__ import annotations

from typing import Any, Dict, List

from .config import DEFAULT_CONFIG, MODEL_VERSION, PHASE_ID


def validate_qa42(
    *,
    populations: Dict[str, Any],
    reconciliation: Dict[str, Any],
    audit_rows: List[Dict[str, Any]],
    contamination: Dict[str, Any],
    regression: Dict[str, Any],
    tests: Dict[str, Any],
    determinism: Dict[str, Any],
) -> Dict[str, Any]:
    cfg = DEFAULT_CONFIG
    checks: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"gate": name, "pass": bool(ok), "detail": detail})

    add(
        "GATE_1_baseline_population",
        int(populations.get("original_dropped") or 0) == cfg.expected_original_dropped,
        populations.get("original_dropped"),
    )
    add(
        "GATE_2_envelope_population",
        int(populations.get("envelope_count") or 0) == cfg.expected_envelope_population,
        populations.get("envelope_count"),
    )
    add(
        "GATE_3_high_population",
        int(populations.get("high_count") or 0) == cfg.expected_high_envelope_population,
        populations.get("high_count"),
    )
    add(
        "GATE_4_recovery_accounting",
        bool(reconciliation.get("examined_equals_accounted"))
        and bool(reconciliation.get("high_equals_examined")),
        {
            "examined": reconciliation.get("recovery_examined"),
            "accounted": reconciliation.get("accounted"),
        },
    )
    add(
        "GATE_5_stable_keys",
        (contamination.get("duplicate_stable_key_count") or 0) == 0,
        contamination.get("duplicate_stable_key_count"),
    )
    add(
        "GATE_6_cross_beam_contamination",
        (contamination.get("cross_beam_contamination_count") or 0) == 0
        and bool(contamination.get("pass")),
        contamination.get("cross_beam_contamination_count"),
    )
    add(
        "GATE_7_existing_ownership_engine",
        all(
            (not r.get("recovery_candidate_generated"))
            or (r.get("engine_path") not in (None, "none") or r.get("final_ownership_decision"))
            for r in audit_rows
        ),
        "generated candidates have engine path / decision",
    )
    add(
        "GATE_8_ownership_safety",
        all(not r.get("qa42_assigned_ownership") for r in audit_rows),
        "qa42_assigned_ownership all False",
    )
    add(
        "GATE_9_regression",
        regression.get("regression_status") == "PASS",
        regression.get("regression_status"),
    )
    add(
        "GATE_10_fifth_sixth_isolation",
        int(populations.get("fifth_set_recovery_population") or 0) == 0
        and int(populations.get("sixth_set_recovery_population") or 0) == 0,
        {
            "fifth": populations.get("fifth_set_recovery_population"),
            "sixth": populations.get("sixth_set_recovery_population"),
        },
    )
    add(
        "GATE_11_determinism",
        determinism.get("determinism_status") == "PASS",
        determinism.get("determinism_status"),
    )
    add(
        "GATE_12_reconciliation",
        bool(reconciliation.get("examined_equals_accounted"))
        and int(reconciliation.get("unresolved") or 0) == 0,
        {
            "accounted": reconciliation.get("accounted"),
            "unresolved": reconciliation.get("unresolved"),
        },
    )
    add(
        "TEST_CASES",
        bool(tests.get("all_pass")),
        tests.get("failed"),
    )

    overall = all(c["pass"] for c in checks)
    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "overall_pass": overall,
        "status": "PASS" if overall else "FAIL",
        "checks": checks,
        "failed_gates": [c["gate"] for c in checks if not c["pass"]],
    }
