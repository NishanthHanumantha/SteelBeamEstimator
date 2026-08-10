"""
QA.4.3 validation gates.
MODEL_VERSION: 10.5.2
"""
from __future__ import annotations

from typing import Any, Dict, List

from .config import DEFAULT_CONFIG, MODEL_VERSION, PHASE_ID


def validate_qa43(
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
        "GATE_leader_population_23",
        int(populations.get("leader_count") or 0) == cfg.expected_leader_population,
        populations.get("leader_count"),
    )
    add(
        "GATE_dropped_104",
        int(populations.get("original_dropped") or 0) == cfg.expected_original_dropped,
        populations.get("original_dropped"),
    )
    add(
        "GATE_accounting",
        bool(reconciliation.get("examined_equals_accounted"))
        and bool(reconciliation.get("leader_equals_examined")),
        {
            "examined": reconciliation.get("recovery_examined"),
            "accounted": reconciliation.get("accounted"),
        },
    )
    add(
        "GATE_stable_keys",
        (contamination.get("duplicate_stable_key_count") or 0) == 0,
        contamination.get("duplicate_stable_key_count"),
    )
    add(
        "GATE_contamination",
        (contamination.get("cross_beam_contamination_count") or 0) == 0
        and bool(contamination.get("pass")),
        contamination.get("cross_beam_contamination_count"),
    )
    add(
        "GATE_engine_path",
        all(
            (not r.get("recovery_candidate_generated"))
            or r.get("engine_path") not in (None, "none")
            for r in audit_rows
        ),
    )
    add(
        "GATE_ownership_safety",
        all(not r.get("qa43_assigned_ownership") for r in audit_rows)
        and all(not r.get("recovery_changed_decision") for r in audit_rows)
        and all(r.get("production_envelope_unchanged") for r in audit_rows),
    )
    add(
        "GATE_regression",
        regression.get("regression_status") == "PASS",
        regression.get("regression_status"),
    )
    add(
        "GATE_fifth_sixth",
        int(populations.get("fifth_set_recovery_population") or 0) == 0
        and int(populations.get("sixth_set_recovery_population") or 0) == 0,
        {
            "fifth": populations.get("fifth_set_recovery_population"),
            "sixth": populations.get("sixth_set_recovery_population"),
        },
    )
    add(
        "GATE_determinism",
        determinism.get("determinism_status") == "PASS",
        determinism.get("determinism_status"),
    )
    add(
        "GATE_unresolved_zero",
        int(reconciliation.get("unresolved") or 0) == 0,
        reconciliation.get("unresolved"),
    )
    add("GATE_tests", bool(tests.get("all_pass")), tests.get("failed"))

    overall = all(c["pass"] for c in checks)
    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "overall_pass": overall,
        "status": "PASS" if overall else "FAIL",
        "checks": checks,
        "failed_gates": [c["gate"] for c in checks if not c["pass"]],
    }
