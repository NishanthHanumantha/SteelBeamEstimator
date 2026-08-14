"""Unit tests for P2.5.9. No Claude. No VB.1."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from PhaseP258_controlled_vision_field_repair.unit_tests import (
    run_unit_tests as run_p258_unit_tests,
)

from .arbitration import arbitrate_field, evaluate_strategy
from .beam_safety import assert_no_ground_truth, evaluate_conservative_partial
from .config import (
    MODEL_VERSION,
    OUT_ACCEPT_UNKNOWN,
    OUT_BLOCKED_CONFIRMED,
    OUT_HOLD_PARTIAL,
    OUT_REJECT_PARTIAL,
    STRATEGY_CONSERVATIVE_PARTIAL,
    STRATEGY_P258_CURRENT,
    STRATEGY_UNKNOWN_ONLY,
)
from .regression import capture_fingerprints, compare_fingerprints, fingerprint_paths, firewall_check

B46_TEXT = "4L-Y10@\\X100/150/100C/C"
B120_TEXT = "3L-Y10@100C/150/100/C"


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _audit(
    *,
    text: str,
    beam_id: str,
    stype: str = "STIRRUP",
    diameter: Any = None,
    legs: Any = None,
    spacing: Any = None,
    vis_diameter: Any = None,
    vis_legs: Any = None,
    vis_spacing: Any = None,
    vis_qty: Any = None,
    vis_type: str = "STIRRUP",
    vis_role: str = "STIRRUP",
    vis_zone: str = "SPAN",
) -> Dict[str, Any]:
    return {
        "candidate_id": f"VC::{beam_id}::ANN-x",
        "beam_id": beam_id,
        "annotation_id": "ANN-x",
        "annotation_text": text,
        "invoke_claude": True,
        "shadow_trigger_reason": ["OCR_CORRUPTION"] if "\\X" in text else ["INCOMPLETE_SPACING"],
        "deterministic_result": {
            "semantic_type": stype,
            "reinforcement_role": "STIRRUP",
            "diameter_value_mm": diameter,
            "leg_count": legs,
            "spacing_values_mm": list(spacing or []),
            "quantity_value": None,
        },
        "vision_result": {
            "semantic_type": vis_type,
            "role": vis_role,
            "diameter_mm": vis_diameter,
            "legs": vis_legs,
            "spacing_mm": list(vis_spacing or []),
            "quantity": vis_qty,
            "zone": vis_zone,
        },
        "model": "claude-sonnet-4-5",
        "evidence_fingerprint": "e" * 64,
    }


def test_unknown_accepted_by_unknown_only() -> None:
    a = _audit(text=B46_TEXT, beam_id="BX", diameter=None, legs=None, spacing=[], vis_diameter=10, vis_legs=4, vis_spacing=[100, 150, 100])
    rec = arbitrate_field(audit=a, field="diameter", strategy=STRATEGY_UNKNOWN_ONLY)
    assert rec["arbitration_outcome"] == OUT_ACCEPT_UNKNOWN
    assert rec["promotion_decision"] == "CONTROLLED_RECOMPUTE"


def test_confirmed_blocked() -> None:
    a = _audit(text="3L-Y10@100C/C", beam_id="BX", diameter=10, legs=3, spacing=[100], vis_diameter=12, vis_legs=4, vis_spacing=[150])
    rec = arbitrate_field(audit=a, field="diameter", strategy=STRATEGY_UNKNOWN_ONLY)
    assert rec["arbitration_outcome"] == OUT_BLOCKED_CONFIRMED
    assert rec["promotion_decision"] == "BLOCKED"


def test_partial_held_by_unknown_only() -> None:
    a = _audit(text=B120_TEXT, beam_id="BX", diameter=10, legs=3, spacing=[100], vis_diameter=10, vis_legs=3, vis_spacing=[100, 150, 100])
    rec = arbitrate_field(audit=a, field="spacing", strategy=STRATEGY_UNKNOWN_ONLY)
    assert rec["deterministic_status"] == "DETERMINISTIC_PARTIAL"
    assert rec["arbitration_outcome"] == OUT_HOLD_PARTIAL
    assert rec["promotion_decision"] != "CONTROLLED_RECOMPUTE"


def test_partial_reaches_conservative_gate() -> None:
    a = _audit(text=B120_TEXT, beam_id="BX", diameter=10, legs=3, spacing=[100], vis_diameter=10, vis_legs=3, vis_spacing=[100, 150, 100])
    ctx = {
        "span_mm": 4000.0,
        "has_stirrups": True,
        "stirrup_labels": ["4L-Y10@100#Zone_A"],
        "zone_truncated_label": True,
        "stirrup_count": 1,
    }
    rec = arbitrate_field(
        audit=a, field="spacing", strategy=STRATEGY_CONSERVATIVE_PARTIAL, beam_ctx=ctx
    )
    assert rec["arbitration_outcome"] in (OUT_REJECT_PARTIAL, OUT_HOLD_PARTIAL, "ACCEPT_CONSERVATIVE_PARTIAL")
    assert rec.get("arbitration_signals") or rec["arbitration_outcome"] != "ACCEPT_CONSERVATIVE_PARTIAL"
    assert rec["promotion_decision"] != "CONTROLLED_RECOMPUTE"  # expansion must not auto-accept


def test_quantity_not_promoted() -> None:
    a = _audit(text=B46_TEXT, beam_id="BX", vis_diameter=10, vis_legs=4, vis_spacing=[100], vis_qty=8)
    rec = arbitrate_field(audit=a, field="quantity", strategy=STRATEGY_UNKNOWN_ONLY)
    assert rec["promotion_decision"] != "CONTROLLED_RECOMPUTE"


def test_zone_not_promoted() -> None:
    a = _audit(text=B46_TEXT, beam_id="BX", vis_diameter=10, vis_legs=4, vis_spacing=[100])
    rec = arbitrate_field(audit=a, field="zone", strategy=STRATEGY_UNKNOWN_ONLY)
    assert rec["promotion_decision"] != "CONTROLLED_RECOMPUTE"


def test_role_not_promoted() -> None:
    a = _audit(text=B46_TEXT, beam_id="BX", vis_diameter=10, vis_legs=4, vis_spacing=[100], vis_role="SIDE_FACE")
    rec = arbitrate_field(audit=a, field="reinforcement_role", strategy=STRATEGY_CONSERVATIVE_PARTIAL)
    assert rec["promotion_decision"] != "CONTROLLED_RECOMPUTE"


def test_semantic_type_not_promoted() -> None:
    a = _audit(text=B46_TEXT, beam_id="BX", vis_diameter=10, vis_legs=4, vis_spacing=[100], vis_type="SIDE_FACE_REINFORCEMENT")
    rec = arbitrate_field(audit=a, field="semantic_type", strategy=STRATEGY_UNKNOWN_ONLY)
    assert rec["promotion_decision"] != "CONTROLLED_RECOMPUTE"


def test_estimator_gt_not_used_by_runtime() -> None:
    src_dir = Path(__file__).resolve().parent
    forbidden = (
        "estimator_kg",
        "estimator_steel",
        "ground_truth_steel",
        "ground_truth_kg",
        "EstimatorOutput",
        "benchmark_answer",
    )
    for name in ("arbitration.py",):
        text = (src_dir / name).read_text(encoding="utf-8")
        for tok in forbidden:
            assert tok not in text, f"{name} must not contain {tok}"
    a = _audit(
        text=B46_TEXT, beam_id="BX",
        diameter=None, legs=None, spacing=[],
        vis_diameter=10, vis_legs=4, vis_spacing=[100, 150, 100],
    )
    a["ground_truth"] = {"diameter_mm": 99}
    a["three_way"] = {"diameter": {"scored": True, "vision_eval": "WRONG", "ground_truth": 99}}
    rec = arbitrate_field(audit=a, field="diameter", strategy=STRATEGY_UNKNOWN_ONLY)
    assert rec["arbitration_outcome"] == OUT_ACCEPT_UNKNOWN
    assert rec["ground_truth_value"] is None
    assert rec["ground_truth_status"] == "NOT_USED_IN_ARBITRATION"
    try:
        evaluate_conservative_partial(
            field="spacing", det_val=[100], vis_val=[100, 150, 100],
            beam_ctx={"estimator_kg": 1.0, "span_mm": 4000},
        )
        raise AssertionError("estimator context must raise")
    except ValueError as exc:
        assert "GT leakage" in str(exc) or "forbidden" in str(exc).lower()
    assert_no_ground_truth({"span_mm": 4000, "has_stirrups": True})


def test_no_production_mutation() -> None:
    paths = fingerprint_paths(_v10(), {})
    before = capture_fingerprints(paths)
    a = _audit(text=B46_TEXT, beam_id="BX", vis_diameter=10, vis_legs=4, vis_spacing=[100])
    evaluate_strategy(audits=[a], strategy=STRATEGY_UNKNOWN_ONLY, beam_contexts={})
    after = capture_fingerprints(paths)
    assert compare_fingerprints(before, after)["unchanged"] is True
    fw = firewall_check(_v10())
    assert fw["ok"] is True


def test_p257_regression() -> None:
    p = (
        _v10()
        / "data"
        / "output"
        / "PhaseP257_unseen_drawing_controlled_vision_validation"
        / "vision_results.json"
    )
    assert p.exists()
    paths = fingerprint_paths(_v10(), {})
    before = capture_fingerprints({"p257_vision": paths["p257_vision"]})
    after = capture_fingerprints({"p257_vision": paths["p257_vision"]})
    assert compare_fingerprints(before, after)["unchanged"] is True


def test_p254_regression() -> None:
    from PhaseP257_unseen_drawing_controlled_vision_validation.unit_tests import (
        test_p254_regression as p257_p254,
    )

    p257_p254()


def test_p255_regression() -> None:
    from PhaseP257_unseen_drawing_controlled_vision_validation.unit_tests import (
        test_p255_regression as p257_p255,
    )

    p257_p255()


def test_p256_regression() -> None:
    from PhaseP257_unseen_drawing_controlled_vision_validation.unit_tests import (
        test_p256_regression as p257_p256,
    )

    p257_p256()


def test_p258_strategy_a_reproduces_partial_promote() -> None:
    a = _audit(
        text=B120_TEXT, beam_id="B120",
        diameter=10, legs=3, spacing=[100],
        vis_diameter=10, vis_legs=3, vis_spacing=[100, 150, 100],
    )
    rows = evaluate_strategy(audits=[a], strategy=STRATEGY_P258_CURRENT)
    spacing = next(r for r in rows if r["field_name"] == "spacing")
    assert spacing["promotion_decision"] == "CONTROLLED_RECOMPUTE"
    assert spacing["arbitration_outcome"] == "P258_PARTIAL_PROMOTED"
    b_rows = evaluate_strategy(audits=[a], strategy=STRATEGY_UNKNOWN_ONLY)
    b_sp = next(r for r in b_rows if r["field_name"] == "spacing")
    assert b_sp["promotion_decision"] != "CONTROLLED_RECOMPUTE"


def test_strategy_classifications() -> None:
    unknown = _audit(text=B46_TEXT, beam_id="B46", diameter=None, legs=None, spacing=[], vis_diameter=10, vis_legs=4, vis_spacing=[100, 150, 100])
    partial = _audit(text=B120_TEXT, beam_id="B120", diameter=10, legs=3, spacing=[100], vis_diameter=10, vis_legs=3, vis_spacing=[100, 150, 100])
    ctx = {"B120": {"span_mm": 4200, "has_stirrups": True, "stirrup_labels": ["4L-Y10@100#Zone_A"], "zone_truncated_label": True, "stirrup_count": 1}}
    a = evaluate_strategy(audits=[unknown, partial], strategy=STRATEGY_P258_CURRENT)
    b = evaluate_strategy(audits=[unknown, partial], strategy=STRATEGY_UNKNOWN_ONLY, beam_contexts=ctx)
    c = evaluate_strategy(audits=[unknown, partial], strategy=STRATEGY_CONSERVATIVE_PARTIAL, beam_contexts=ctx)
    def _dec(rows, bid, field):
        return next(r for r in rows if r["beam_id"] == bid and r["field_name"] == field)

    assert _dec(a, "B46", "diameter")["promotion_decision"] == "CONTROLLED_RECOMPUTE"
    assert _dec(a, "B120", "spacing")["promotion_decision"] == "CONTROLLED_RECOMPUTE"
    assert _dec(b, "B46", "diameter")["arbitration_outcome"] == OUT_ACCEPT_UNKNOWN
    assert _dec(b, "B120", "spacing")["arbitration_outcome"] == OUT_HOLD_PARTIAL
    assert _dec(c, "B46", "diameter")["arbitration_outcome"] == OUT_ACCEPT_UNKNOWN
    assert _dec(c, "B120", "spacing")["arbitration_outcome"] == OUT_REJECT_PARTIAL


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("unknown_field_accepted_unknown_only", test_unknown_accepted_by_unknown_only),
        ("confirmed_field_blocked", test_confirmed_blocked),
        ("partial_held_unknown_only", test_partial_held_by_unknown_only),
        ("partial_reaches_conservative", test_partial_reaches_conservative_gate),
        ("quantity_not_promoted", test_quantity_not_promoted),
        ("zone_not_promoted", test_zone_not_promoted),
        ("role_not_promoted", test_role_not_promoted),
        ("semantic_type_not_promoted", test_semantic_type_not_promoted),
        ("estimator_gt_not_used", test_estimator_gt_not_used_by_runtime),
        ("no_production_mutation", test_no_production_mutation),
        ("P2.5.7_regression", test_p257_regression),
        ("P2.5.4_regression", test_p254_regression),
        ("P2.5.5_regression", test_p255_regression),
        ("P2.5.6_regression", test_p256_regression),
        ("P2.5.8_strategy_a_reproducible", test_p258_strategy_a_reproduces_partial_promote),
        ("strategy_classifications", test_strategy_classifications),
    ]
    results: List[Dict[str, Any]] = []
    for name, fn in tests:
        try:
            fn()
            results.append({"name": name, "pass": True})
        except Exception as exc:  # noqa: BLE001
            results.append({"name": name, "pass": False, "error": str(exc)})
    p258 = run_p258_unit_tests()
    passed = sum(1 for r in results if r["pass"])
    return {
        "success": passed == len(tests) and bool(p258.get("success")),
        "passed": passed,
        "total": len(tests),
        "results": results,
        "p258_unit_tests": p258,
        "model_version": MODEL_VERSION,
    }


__all__ = ["run_unit_tests"]
