"""
P2.3.1 acceptance gates + decision classification.
MODEL_VERSION: 10.5.6
"""
from __future__ import annotations

from typing import Any, Dict, List, Set

from .config import (
    EXPECTED_BASELINE_LEADERS,
    EXPECTED_BASELINE_NODES,
    EXPECTED_CONTROLLED_LEADERS,
    EXPECTED_CONTROLLED_NODES,
    EXPECTED_MIGRATED_ENTITIES,
    MODEL_VERSION,
    PHASE_ID,
    PRODUCTION_POLICY,
    DecisionClass,
)


def classify_decision(
    *,
    gates_pass: bool,
    steel_delta_pp: float,
    overall_delta_pp: float,
    workbook_identical: bool,
    negative_regression: bool,
) -> str:
    if not gates_pass or negative_regression:
        return DecisionClass.FAILED.value
    if steel_delta_pp < -0.05 or overall_delta_pp < -0.05:
        return DecisionClass.NEGATIVE.value
    if steel_delta_pp > 0.05 or overall_delta_pp > 0.05:
        return DecisionClass.IMPROVEMENT.value
    return DecisionClass.NEUTRAL.value


def validate_p231(ctx: Dict[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"gate": name, "pass": bool(ok), "detail": detail})

    base_counts = ctx.get("baseline_counts") or {}
    ctrl_counts = ctx.get("controlled_counts") or {}
    migrations: List[Dict[str, Any]] = ctx.get("migrations") or []
    mig_ids = {m.get("entity_id") for m in migrations}
    expected = set(EXPECTED_MIGRATED_ENTITIES)

    add(
        "GATE_01_baseline_reproduces_P23",
        int(base_counts.get("accepted_node_total") or 0) == EXPECTED_BASELINE_NODES
        and int(base_counts.get("accepted_leaders") or 0) == EXPECTED_BASELINE_LEADERS,
        base_counts,
    )
    add(
        "GATE_02_controlled_uses_only_E_STRONG_COMBINED",
        all(
            m.get("recovery_policy") == PRODUCTION_POLICY and m.get("source") == "P2.2"
            for m in migrations
        )
        and ctx.get("production_policy") == PRODUCTION_POLICY,
        {"policy": ctx.get("production_policy"), "migrations": len(migrations)},
    )
    add(
        "GATE_03_expected_B16_chain_present",
        expected.issubset(mig_ids)
        and "LDR::7A1FFD68"
        in set(
            (
                (
                    (ctx.get("controlled_ownership") or {}).get("by_beam") or {}
                ).get("B16")
                or {}
            ).get("accepted_node_ids")
            or []
        ),
        sorted(mig_ids),
    )
    add(
        "GATE_04_no_policy_D",
        all(m.get("recovery_policy") != "D_CHAIN_GEOMETRIC" for m in migrations),
    )
    unexpected_own = sorted(mig_ids - expected)
    add(
        "GATE_05_no_unexpected_ownership_migration",
        len(unexpected_own) == 0
        and int(ctrl_counts.get("accepted_node_total") or 0) == EXPECTED_CONTROLLED_NODES
        and int(ctrl_counts.get("accepted_leaders") or 0) == EXPECTED_CONTROLLED_LEADERS,
        {"unexpected": unexpected_own, "counts": ctrl_counts},
    )

    # Engineering migration: workbook entity deltas beyond identical = unexpected if not B16-only
    wb_identical = bool(
        (ctx.get("comparison") or {})
        .get("workbook", {})
        .get("identical_engineering_content")
    )
    eng_unexpected = ctx.get("unexpected_engineering_changes") or []
    add(
        "GATE_06_no_unexpected_engineering_migration",
        len(eng_unexpected) == 0,
        eng_unexpected,
    )
    add(
        "GATE_07_baseline_engineering_output_generated",
        bool((ctx.get("baseline_wb") or {}).get("ok")),
        (ctx.get("baseline_wb") or {}).get("path"),
    )
    add(
        "GATE_08_controlled_engineering_output_generated",
        bool((ctx.get("controlled_wb") or {}).get("ok")),
        (ctx.get("controlled_wb") or {}).get("path"),
    )
    add(
        "GATE_09_B16_downstream_trace_complete",
        bool((ctx.get("b16_trace") or {}).get("stages"))
        and len((ctx.get("b16_trace") or {}).get("stages") or []) >= 5,
    )
    add(
        "GATE_10_QA3_benchmark_completed",
        bool((ctx.get("baseline_bench") or {}).get("compared"))
        and bool((ctx.get("controlled_bench") or {}).get("compared")),
    )
    add(
        "GATE_11_baseline_vs_controlled_comparison_completed",
        bool(ctx.get("comparison")),
    )
    add(
        "GATE_12_no_historical_T18_regression",
        ctx.get("historical_t18_hash_before") == ctx.get("historical_t18_hash_after")
        and ctx.get("historical_t18_hash_before") is not None,
        {
            "before": ctx.get("historical_t18_hash_before"),
            "after": ctx.get("historical_t18_hash_after"),
        },
    )
    add(
        "GATE_13_determinism",
        (ctx.get("determinism") or {}).get("determinism_status") == "PASS",
        (ctx.get("determinism") or {}).get("determinism_status"),
    )
    add(
        "GATE_14_no_contamination",
        not ctx.get("contamination_found"),
        ctx.get("contamination_found"),
    )
    add(
        "GATE_15_output_integrity",
        bool(ctx.get("outputs_ok")),
    )
    add(
        "GATE_unit_tests",
        (ctx.get("unit_tests") or {}).get("overall_pass") is True,
    )

    overall = all(c["pass"] for c in checks)
    steel_pp = (
        ((ctx.get("comparison") or {}).get("qa30_fourth") or {})
        .get("Steel Accuracy", {})
        .get("delta_pp")
    ) or 0.0
    overall_pp = (
        ((ctx.get("comparison") or {}).get("qa30_fourth") or {})
        .get("Overall Accuracy", {})
        .get("delta_pp")
    ) or 0.0

    decision = classify_decision(
        gates_pass=overall,
        steel_delta_pp=float(steel_pp),
        overall_delta_pp=float(overall_pp),
        workbook_identical=wb_identical,
        negative_regression=False,
    )

    ready = decision == DecisionClass.IMPROVEMENT.value
    if decision == DecisionClass.IMPROVEMENT.value:
        recommendation = (
            "Engineering improvement observed under controlled ownership. "
            "Proceed to broader E_STRONG_COMBINED validation only after reviewing "
            "regression, contamination, and cross-beam behaviour."
        )
    elif decision == DecisionClass.NEUTRAL.value:
        recommendation = (
            "Keep E_STRONG_COMBINED controlled/diagnostic only; do not broaden yet. "
            "Recovered leader does not change R1.3/VB1 steel quantities in the current "
            "architecture (ownership is applied after Excel generation)."
        )
    elif decision == DecisionClass.NEGATIVE.value:
        recommendation = (
            "Keep E_STRONG_COMBINED disabled from broader validation; identify the "
            "exact downstream causal point causing accuracy regression."
        )
    else:
        recommendation = (
            "Controlled recompute failed gates; fix reproducibility/traceability "
            "before any broader validation."
        )

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "overall_pass": overall and decision != DecisionClass.FAILED.value,
        "status": "PASS" if overall and decision != DecisionClass.FAILED.value else "FAIL",
        "decision": decision,
        "checks": checks,
        "failed_gates": [c["gate"] for c in checks if not c["pass"]],
        "broader_e_validation": "READY" if ready else "NOT READY",
        "recommendation": recommendation,
    }
