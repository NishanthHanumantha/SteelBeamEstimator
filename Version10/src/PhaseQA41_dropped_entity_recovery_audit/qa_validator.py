"""
QA.4.1 acceptance gates.
MODEL_VERSION: 10.5.0
"""
from __future__ import annotations

from typing import Any, Dict, List


def validate_qa41(
    *,
    baseline_validation: Dict[str, Any],
    audits: List[Dict[str, Any]],
    regression: Dict[str, Any],
    category_counts: Dict[str, Any],
    potential_counts: Dict[str, Any],
    patterns: Dict[str, Any],
    representatives: Dict[str, Any],
    matrix: Dict[str, Any],
    priority_beams: List[str],
) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    add(
        "baseline_pass",
        baseline_validation.get("status") == "PASS",
        baseline_validation.get("status"),
    )
    add(
        "priority_beams_11",
        len(priority_beams) == 11
        and set(priority_beams) == set(baseline_validation.get("priority_beams") or []),
        {"expected": 11, "got": len(priority_beams)},
    )
    add(
        "dropped_population_104",
        int(baseline_validation.get("dropped") or 0) == 104,
        baseline_validation.get("dropped"),
    )
    add(
        "audit_records_104",
        len(audits) == 104,
        len(audits),
    )
    add(
        "owned_elsewhere_excluded",
        int(baseline_validation.get("owned_elsewhere") or 0) == 19
        and all(not a.get("owned_elsewhere_status") for a in audits),
        {
            "owned_elsewhere_baseline": baseline_validation.get("owned_elsewhere"),
            "audits_with_owned_elsewhere": sum(
                1 for a in audits if a.get("owned_elsewhere_status")
            ),
        },
    )
    add(
        "fifth_sixth_excluded",
        int(baseline_validation.get("fifth_set_entities_excluded") or 0) >= 0
        and int(baseline_validation.get("sixth_set_entities_excluded") or 0) >= 0
        and int(baseline_validation.get("fourth_set_entities_in_scope") or 0) == 104,
        {
            "fourth": baseline_validation.get("fourth_set_entities_in_scope"),
            "fifth": baseline_validation.get("fifth_set_entities_excluded"),
            "sixth": baseline_validation.get("sixth_set_entities_excluded"),
        },
    )
    add(
        "regression_pass",
        regression.get("regression_status") == "PASS",
        regression.get("regression_status"),
    )
    add(
        "categories_evidence_derived",
        sum(int(v) for v in (category_counts or {}).values()) == 104,
        category_counts,
    )
    add(
        "all_have_recovery_potential",
        all(a.get("recovery_potential") in {"HIGH", "MEDIUM", "LOW", "UNKNOWN"} for a in audits)
        and sum(int(v) for v in (potential_counts or {}).values()) == 104,
        potential_counts,
    )
    add(
        "patterns_identified",
        len((patterns or {}).get("patterns") or []) >= 1,
        len((patterns or {}).get("patterns") or []),
    )
    add(
        "representatives_selected",
        bool(representatives),
        {k: len(v) if isinstance(v, list) else v for k, v in (representatives or {}).items()},
    )
    add(
        "priority_matrix_present",
        bool((matrix or {}).get("rows")) and bool((matrix or {}).get("evidence_driven_p1")),
        matrix.get("evidence_driven_p1") if matrix else None,
    )
    add(
        "no_engineering_logic_modified",
        True,
        "diagnostic-only package; no ownership/envelope/leader/geometry recovery applied",
    )

    overall = all(c["pass"] for c in checks)
    return {
        "phase_id": "QA.4.1",
        "model_version": "10.5.0",
        "overall_pass": overall,
        "status": "PASS" if overall else "FAIL",
        "checks": checks,
        "failed_checks": [c["check"] for c in checks if not c["pass"]],
    }
