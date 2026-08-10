"""
P2.2 acceptance gates.
MODEL_VERSION: 10.5.4
"""
from __future__ import annotations

from typing import Any, Dict, List

from .config import (
    DEFAULT_CONFIG,
    KNOWN_NEGATIVE_KEYS,
    MODEL_VERSION,
    PHASE_ID,
    PRODUCTION_POLICY,
    REFERENCE_POSITIVE_KEY,
    EnhancedDecision,
    ProductionGate,
)


def validate_p22(
    *,
    population: Dict[str, Any],
    analysis: Dict[str, Any],
    regression: Dict[str, Any],
    determinism: Dict[str, Any],
    unit_test_result: Dict[str, Any],
) -> Dict[str, Any]:
    cfg = DEFAULT_CONFIG
    checks: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"gate": name, "pass": bool(ok), "detail": detail})

    decisions = analysis.get("decisions") or []
    by_key = {d.get("stable_key"): d for d in decisions}
    summary = analysis.get("summary") or {}
    comparison = analysis.get("policy_comparison") or {}
    counts = comparison.get("accepted_count_all_23") or {}
    elig = comparison.get("accepted_count_among_5_eligible") or {}

    add(
        "GATE_23_leaders",
        int(population.get("leader_count") or 0) == cfg.expected_leader_count
        and len(decisions) == cfg.expected_leader_count,
        population.get("leader_count"),
    )
    add(
        "GATE_5_eligible",
        int(population.get("eligible_count") or 0) == cfg.expected_eligible_count,
        population.get("eligible_count"),
    )
    add(
        "GATE_policy_E_count_all",
        counts.get(PRODUCTION_POLICY) == cfg.expected_policy_e_accept_all,
        counts.get(PRODUCTION_POLICY),
    )
    add(
        "GATE_policy_E_count_eligible",
        elig.get(PRODUCTION_POLICY) == cfg.expected_policy_e_accept_eligible,
        elig.get(PRODUCTION_POLICY),
    )
    add(
        "GATE_policy_A_zero",
        counts.get("A_CURRENT") == 0,
        counts.get("A_CURRENT"),
    )

    ref = by_key.get(REFERENCE_POSITIVE_KEY)
    add(
        "GATE_B16_reference_accept_candidate",
        bool(ref)
        and ref.get("enhanced_decision") == EnhancedDecision.ACCEPT_CANDIDATE.value
        and ref.get("enhanced_policy") == PRODUCTION_POLICY,
        {
            "present": bool(ref),
            "decision": (ref or {}).get("enhanced_decision"),
            "reason": (ref or {}).get("enhanced_reason"),
        },
    )

    neg_fail = []
    for nk in KNOWN_NEGATIVE_KEYS:
        d = by_key.get(nk)
        if d is None:
            continue  # may be absent if not in the 23; skip
        if d.get("enhanced_decision") == EnhancedDecision.ACCEPT_CANDIDATE.value:
            neg_fail.append(nk)
    add(
        "GATE_known_negatives_rejected",
        len(neg_fail) == 0,
        {"checked": [k for k in KNOWN_NEGATIVE_KEYS if k in by_key], "failed": neg_fail},
    )

    # Contaminated leaders must never be ACCEPT_CANDIDATE
    contam_accepted = [
        d.get("stable_key")
        for d in decisions
        if (
            d.get("neighbour_ambiguity") or d.get("inside_other_beam_envelope")
        )
        and d.get("enhanced_decision") == EnhancedDecision.ACCEPT_CANDIDATE.value
    ]
    add("GATE_contamination_not_accepted", len(contam_accepted) == 0, contam_accepted)

    # D must not be production policy
    add(
        "GATE_production_policy_is_E_not_D",
        summary.get("production_policy") == PRODUCTION_POLICY
        and summary.get("production_policy") != "D_CHAIN_GEOMETRIC",
        summary.get("production_policy"),
    )

    add(
        "GATE_diagnostic_gate",
        analysis.get("production_gate") == ProductionGate.DIAGNOSTIC_ONLY.value
        and analysis.get("beam_ownership_written") is False,
        analysis.get("production_gate"),
    )
    add(
        "GATE_regression",
        regression.get("regression_status") == "PASS",
        regression.get("regression_status"),
    )
    add(
        "GATE_owned_hash_unchanged",
        regression.get("baseline_owned_hash") == regression.get("current_owned_hash")
        and regression.get("baseline_owned_hash") is not None,
    )
    add(
        "GATE_t18_hash_unchanged",
        regression.get("baseline_t18_hash") == regression.get("current_t18_hash")
        and regression.get("baseline_t18_hash") is not None,
    )
    add(
        "GATE_determinism",
        determinism.get("determinism_status") == "PASS",
        determinism.get("determinism_status"),
    )
    add(
        "GATE_unit_tests",
        unit_test_result.get("overall_pass") is True,
        {
            "passed": unit_test_result.get("passed"),
            "failed": unit_test_result.get("failed"),
        },
    )
    add(
        "GATE_fifth_sixth",
        int(population.get("fifth_set_count") or 0) == 0
        and int(population.get("sixth_set_count") or 0) == 0,
    )
    add(
        "GATE_complete_decisions",
        all(
            d.get("enhanced_decision")
            and d.get("enhanced_policy")
            and d.get("enhanced_reason")
            for d in decisions
        ),
    )

    overall = all(c["pass"] for c in checks)
    ready = overall and analysis.get("beam_ownership_written") is False
    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "overall_pass": overall,
        "status": "PASS" if overall else "FAIL",
        "checks": checks,
        "failed_gates": [c["gate"] for c in checks if not c["pass"]],
        "ready_for_controlled_production_gate": ready,
        "label": "DIAGNOSTIC / PRODUCTION-CANDIDATE ONLY",
    }
