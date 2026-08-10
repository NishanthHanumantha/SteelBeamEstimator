"""
P2.3 acceptance gates + final decision classification.
MODEL_VERSION: 10.5.5
"""
from __future__ import annotations

from typing import Any, Dict, List

from .config import (
    DEFAULT_CONFIG,
    MODEL_VERSION,
    PHASE_ID,
    PRODUCTION_POLICY,
    REFERENCE_POSITIVE_KEY,
    DecisionClass,
)
from .regression import validate_no_unexplained_migration


def classify_decision(
    *,
    gates_pass: bool,
    contamination: bool,
    unexplained: bool,
    nondeterministic: bool,
    ownership_or_render_improvement: bool,
    material_improvement: bool,
    steel_regenerated: bool,
    steel_delta_pp: float,
) -> str:
    if nondeterministic:
        return DecisionClass.FAIL_NONDETERMINISTIC.value
    if contamination:
        return DecisionClass.FAIL_CONTAMINATION.value
    if unexplained:
        return DecisionClass.FAIL_UNEXPLAINED.value
    if not gates_pass:
        return DecisionClass.FAIL_REGRESSION.value
    if material_improvement and steel_delta_pp > 0.05:
        return DecisionClass.PASS_CONTROLLED_IMPROVEMENT.value
    if ownership_or_render_improvement and (not steel_regenerated or steel_delta_pp == 0):
        if ownership_or_render_improvement and not steel_regenerated:
            return DecisionClass.PASS_DIAGNOSTIC_UNCLEAR.value
        return DecisionClass.PASS_SAFE_NO_MATERIAL.value
    if ownership_or_render_improvement:
        return DecisionClass.PASS_SAFE_NO_MATERIAL.value
    return DecisionClass.PASS_SAFE_NO_MATERIAL.value


def validate_p23(
    *,
    population_leader_count: int,
    gate: Dict[str, Any],
    baseline_mode_equal: bool,
    migrations: List[Dict[str, Any]],
    analysis: Dict[str, Any],
    regression: Dict[str, Any],
    determinism: Dict[str, Any],
    unit_tests: Dict[str, Any],
    render_comparison: Dict[str, Any],
    accuracy: Dict[str, Any],
    mode: str = "CONTROLLED",
) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    controlled = mode.upper() == "CONTROLLED"

    def add(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"gate": name, "pass": bool(ok), "detail": detail})

    add(
        "GATE_explicit_production_gate",
        gate.get("leader_chain_recovery_policy") == PRODUCTION_POLICY
        and "leader_chain_recovery_enabled" in gate,
        gate,
    )
    add("GATE_baseline_reproduces_ownership", baseline_mode_equal)
    add(
        "GATE_controlled_only_E",
        all(
            m.get("recovery_policy") == PRODUCTION_POLICY and m.get("source") == "P2.2"
            for m in migrations
        ),
        len(migrations),
    )
    ctrl_own = analysis.get("controlled_ownership") or {}
    b16 = ((ctrl_own.get("by_beam") or {}).get("B16") or {})
    add(
        "GATE_B16_leader_effectively_owned",
        (not controlled)
        or ("LDR::7A1FFD68" in set(b16.get("accepted_node_ids") or [])),
        {"mode": mode, "owned": "LDR::7A1FFD68" in set(b16.get("accepted_node_ids") or [])},
    )
    add(
        "GATE_no_policy_D",
        all(m.get("recovery_policy") != "D_CHAIN_GEOMETRIC" for m in migrations),
    )
    add(
        "GATE_no_neighbour_contamination",
        not render_comparison.get("any_neighbour_contamination")
        and all(
            not (m.get("contamination_checks") or {}).get("neighbour_ambiguity")
            for m in migrations
            if m.get("entity_type") == "Leader"
        ),
    )
    mig_val = validate_no_unexplained_migration(migrations)
    add("GATE_no_unexplained_migration", mig_val["pass"], mig_val)
    add(
        "GATE_propagation_traceable",
        (not controlled) or len(analysis.get("propagation") or []) >= 1,
        len(analysis.get("propagation") or []),
    )
    add(
        "GATE_render_comparison",
        int(render_comparison.get("affected_beam_count") or 0) >= 1,
    )
    add(
        "GATE_B16_render",
        any(r.get("beam_id") == "B16" for r in (render_comparison.get("rows") or [])),
    )
    add("GATE_benchmark_comparison", bool(accuracy.get("AccuracyComparison")))
    add("GATE_regression", regression.get("regression_status") == "PASS")
    add("GATE_determinism", determinism.get("determinism_status") == "PASS")
    add(
        "GATE_historical_t18_unchanged",
        regression.get("baseline_t18_hash") == regression.get("current_t18_hash"),
    )
    add("GATE_unit_tests", unit_tests.get("overall_pass") is True)
    add(
        "GATE_p22_population",
        population_leader_count == DEFAULT_CONFIG.expected_leader_count,
        population_leader_count,
    )
    add(
        "GATE_reference_key_accepted",
        (not controlled)
        or REFERENCE_POSITIVE_KEY in (gate.get("accepted_keys") or []),
        gate.get("accepted_keys"),
    )

    overall = all(c["pass"] for c in checks)
    steel_delta = (
        (
            (accuracy.get("AccuracyComparison") or {})
            .get("overall_three_sets")
            or {}
        )
        .get("Steel Accuracy")
        or {}
    ).get("absolute_pp") or 0.0

    decision = classify_decision(
        gates_pass=overall,
        contamination=bool(render_comparison.get("any_neighbour_contamination")),
        unexplained=not mig_val["pass"],
        nondeterministic=determinism.get("determinism_status") != "PASS",
        ownership_or_render_improvement=bool(
            accuracy.get("ownership_or_render_improvement")
        ),
        material_improvement=bool(accuracy.get("material_improvement")),
        steel_regenerated=bool(accuracy.get("steel_regenerated")),
        steel_delta_pp=float(steel_delta),
    )

    # PASS classes still require gates_pass
    if not overall and not decision.startswith("FAIL"):
        decision = DecisionClass.FAIL_REGRESSION.value

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "overall_pass": overall and decision.startswith("PASS"),
        "status": "PASS" if overall and decision.startswith("PASS") else "FAIL",
        "decision_class": decision,
        "checks": checks,
        "failed_gates": [c["gate"] for c in checks if not c["pass"]],
        "ready_for_broader_e_validation": (
            overall
            and decision == DecisionClass.PASS_CONTROLLED_IMPROVEMENT.value
        ),
        "label": DEFAULT_CONFIG.label,
    }
