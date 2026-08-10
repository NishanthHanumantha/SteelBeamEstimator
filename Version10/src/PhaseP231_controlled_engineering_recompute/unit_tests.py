"""
Focused unit tests for P2.3.1.
MODEL_VERSION: 10.5.6
"""
from __future__ import annotations

from typing import Any, Dict, List

from .comparison import build_comparison
from .config import (
    EXPECTED_MIGRATED_ENTITIES,
    MODEL_VERSION,
    PHASE_ID,
    PRODUCTION_POLICY,
    DecisionClass,
)
from .gates import classify_decision, validate_p231


def run_unit_tests() -> Dict[str, Any]:
    tests: List[Dict[str, Any]] = []

    def add(tid: str, name: str, ok: bool, detail: Any = None) -> None:
        tests.append({"test_id": tid, "name": name, "pass": bool(ok), "detail": detail})

    add(
        "UT_01",
        "expected migrated entities are leader+ARR+LTGT",
        set(EXPECTED_MIGRATED_ENTITIES)
        == {"LDR::7A1FFD68", "ARR::4C3D2D29", "LTGT::LDR::7A1FFD68"},
    )
    add("UT_02", "production policy is E only", PRODUCTION_POLICY == "E_STRONG_COMBINED")

    # Decision classification
    add(
        "UT_03",
        "neutral when steel delta 0 and gates pass",
        classify_decision(
            gates_pass=True,
            steel_delta_pp=0.0,
            overall_delta_pp=0.0,
            workbook_identical=True,
            negative_regression=False,
        )
        == DecisionClass.NEUTRAL.value,
    )
    add(
        "UT_04",
        "improvement when steel delta positive",
        classify_decision(
            gates_pass=True,
            steel_delta_pp=1.0,
            overall_delta_pp=0.5,
            workbook_identical=False,
            negative_regression=False,
        )
        == DecisionClass.IMPROVEMENT.value,
    )
    add(
        "UT_05",
        "negative when steel regresses",
        classify_decision(
            gates_pass=True,
            steel_delta_pp=-1.0,
            overall_delta_pp=-0.5,
            workbook_identical=False,
            negative_regression=False,
        )
        == DecisionClass.NEGATIVE.value,
    )
    add(
        "UT_06",
        "failed when gates fail",
        classify_decision(
            gates_pass=False,
            steel_delta_pp=0.0,
            overall_delta_pp=0.0,
            workbook_identical=True,
            negative_regression=False,
        )
        == DecisionClass.FAILED.value,
    )

    # Comparison helper
    cmp_ = build_comparison(
        baseline_wb={
            "sha256": "a",
            "content_fingerprint": "fp1",
            "steel_kg": 100.0,
            "bar_count": 10,
            "beam_count": 1,
            "b16": {"steel_kg": 5.0, "bar_count": 2},
        },
        controlled_wb={
            "sha256": "b",
            "content_fingerprint": "fp1",
            "steel_kg": 100.0,
            "bar_count": 10,
            "beam_count": 1,
            "b16": {"steel_kg": 5.0, "bar_count": 2},
        },
        baseline_bench={"drawing_summary": {"beam_detection_pct": 78.32, "bar_detection_pct": 39.89, "bar_accuracy_pct": 37.33, "steel_accuracy_pct": 58.39}},
        controlled_bench={"drawing_summary": {"beam_detection_pct": 78.32, "bar_detection_pct": 39.89, "bar_accuracy_pct": 37.33, "steel_accuracy_pct": 58.39}},
        baseline_counts={"accepted_node_total": 288, "accepted_leaders": 25},
        controlled_counts={"accepted_node_total": 291, "accepted_leaders": 26},
        b16_trace={"effect_class": "A_changes_nothing_downstream_for_steel", "architectural_note": "x"},
    )
    add(
        "UT_07",
        "comparison detects identical engineering content",
        cmp_["workbook"]["identical_engineering_content"] is True
        and cmp_["qa30_fourth"]["Steel Accuracy"]["delta_pp"] == 0.0,
    )

    # Gate: unexpected migration fails
    bad = validate_p231(
        {
            "baseline_counts": {"accepted_node_total": 288, "accepted_leaders": 25},
            "controlled_counts": {"accepted_node_total": 291, "accepted_leaders": 26},
            "migrations": [
                {
                    "entity_id": "LDR::7A1FFD68",
                    "source": "P2.2",
                    "recovery_policy": PRODUCTION_POLICY,
                },
                {
                    "entity_id": "ARR::4C3D2D29",
                    "source": "P2.2",
                    "recovery_policy": PRODUCTION_POLICY,
                },
                {
                    "entity_id": "LTGT::LDR::7A1FFD68",
                    "source": "P2.2",
                    "recovery_policy": PRODUCTION_POLICY,
                },
                {
                    "entity_id": "EXTRA::BAD",
                    "source": "P2.2",
                    "recovery_policy": PRODUCTION_POLICY,
                },
            ],
            "production_policy": PRODUCTION_POLICY,
            "controlled_ownership": {
                "by_beam": {"B16": {"accepted_node_ids": list(EXPECTED_MIGRATED_ENTITIES)}}
            },
            "baseline_wb": {"ok": True, "path": "x"},
            "controlled_wb": {"ok": True, "path": "y"},
            "b16_trace": {"stages": [{}] * 6},
            "baseline_bench": {"compared": True},
            "controlled_bench": {"compared": True},
            "comparison": {"workbook": {"identical_bytes": True}, "qa30_fourth": {"Steel Accuracy": {"delta_pp": 0}, "Overall Accuracy": {"delta_pp": 0}}},
            "historical_t18_hash_before": "h",
            "historical_t18_hash_after": "h",
            "determinism": {"determinism_status": "PASS"},
            "contamination_found": False,
            "outputs_ok": True,
            "unit_tests": {"overall_pass": True},
            "unexpected_engineering_changes": [],
        }
    )
    add(
        "UT_08",
        "unexpected ownership migration fails GATE_05",
        "GATE_05_no_unexpected_ownership_migration" in bad["failed_gates"],
        bad["failed_gates"],
    )

    failed = [t for t in tests if not t["pass"]]
    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "overall_pass": len(failed) == 0,
        "passed": sum(1 for t in tests if t["pass"]),
        "failed": len(failed),
        "total": len(tests),
        "tests": tests,
        "failed_ids": [t["test_id"] for t in failed],
    }


if __name__ == "__main__":
    import json
    import sys

    r = run_unit_tests()
    print(json.dumps({k: r[k] for k in ("overall_pass", "passed", "failed", "total", "failed_ids")}, indent=2))
    for t in r["tests"]:
        print(("PASS" if t["pass"] else "FAIL"), t["test_id"], t["name"])
    raise SystemExit(0 if r["overall_pass"] else 1)
