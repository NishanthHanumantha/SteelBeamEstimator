"""
P2.1 acceptance gates.
MODEL_VERSION: 10.5.3
"""
from __future__ import annotations

from typing import Any, Dict, List

from .config import DEFAULT_CONFIG, MODEL_VERSION, PHASE_ID


def validate_p21(
    *,
    population: Dict[str, Any],
    analysis: Dict[str, Any],
    regression: Dict[str, Any],
    determinism: Dict[str, Any],
) -> Dict[str, Any]:
    cfg = DEFAULT_CONFIG
    checks: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"gate": name, "pass": bool(ok), "detail": detail})

    add(
        "GATE_23_leaders",
        int(population.get("leader_count") or 0) == cfg.expected_leader_count
        and len(analysis.get("traces") or []) == cfg.expected_leader_count,
        population.get("leader_count"),
    )
    add(
        "GATE_5_eligible",
        int(population.get("eligible_count") or 0) == cfg.expected_eligible_count
        and len(analysis.get("focus_candidates") or []) == cfg.expected_eligible_count,
        population.get("eligible_count"),
    )
    add(
        "GATE_complete_records",
        all(
            t.get("exact_r2_rejection_condition") is not None
            or t.get("r2_tip_in_envelope_ok") is True
            or t.get("entity_type") == "Annotation"
            for t in (analysis.get("traces") or [])
        ),
    )
    add(
        "GATE_policy_A_matches_t18_rejects",
        all(
            (not (p.get("policy_results") or {}).get("A_CURRENT"))
            for p in (analysis.get("policy_rows") or [])
            if p.get("current_t18_result") == "REJECTED"
        ),
    )
    add(
        "GATE_regression",
        regression.get("regression_status") == "PASS",
        regression.get("regression_status"),
    )
    add(
        "GATE_determinism",
        determinism.get("determinism_status") == "PASS",
        determinism.get("determinism_status"),
    )
    add(
        "GATE_fifth_sixth",
        int(population.get("fifth_set_count") or 0) == 0
        and int(population.get("sixth_set_count") or 0) == 0,
    )
    add(
        "GATE_root_cause_present",
        bool((analysis.get("root_cause") or {}).get("answers"))
        and bool((analysis.get("root_cause") or {}).get("recommended_next_phase")),
    )
    # SAFE counterfactual accepts must not include neighbour/inside flags
    unsafe_safe = []
    for f in analysis.get("focus_candidates") or []:
        for pname in ("B_CHAIN_EVIDENCE", "C_CHAIN_ENDPOINT", "D_CHAIN_GEOMETRIC", "E_STRONG_COMBINED"):
            key = {
                "B_CHAIN_EVIDENCE": "policy_B",
                "C_CHAIN_ENDPOINT": "policy_C",
                "D_CHAIN_GEOMETRIC": "policy_D",
                "E_STRONG_COMBINED": "policy_E",
            }[pname]
            if f.get(key) and f.get("contamination_risk") == "SAFE":
                if f.get("neighbour_ambiguity") or f.get("inside_other_beam_envelope"):
                    unsafe_safe.append(f.get("stable_key"))
    add("GATE_safe_cases_uncontaminated", len(unsafe_safe) == 0, unsafe_safe)
    add(
        "GATE_diagnostic_only",
        (analysis.get("root_cause") or {}).get("production_fix_implemented") is False,
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
