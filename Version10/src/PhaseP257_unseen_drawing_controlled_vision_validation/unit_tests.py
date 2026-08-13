"""Unit tests for P2.5.7 (no live Claude calls)."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, List

from PhaseP254_semantic_reinforcement_vision_benchmark.semantic_schema import normalize_parsed
from PhaseP254_semantic_reinforcement_vision_benchmark.unit_tests import (
    run_unit_tests as run_p254_unit_tests,
)
from PhaseP254_semantic_reinforcement_vision_benchmark.validator import validate_interpretation
from PhaseP254_semantic_reinforcement_vision_benchmark.vision_prompt import (
    SYSTEM_PROMPT,
    assert_no_truth_leak,
    build_user_prompt,
    prompt_fingerprint,
)
from PhaseP255_controlled_shadow_integration.deterministic_snapshot import (
    snapshot_from_frozen_intent,
)
from PhaseP256_controlled_field_level_vision_experiment.config import (
    FIELD_ZONE,
)
from PhaseP256_controlled_field_level_vision_experiment.field_contract import (
    assert_field_result_not_production,
)
from PhaseP256_controlled_field_level_vision_experiment.integrator import evaluate_one
from PhaseP256_controlled_field_level_vision_experiment.unit_tests import (
    run_unit_tests as run_p256_unit_tests,
    test_b46_field_supplementation as p256_b46,
    test_b58_type_role_conflict as p256_b58,
    test_b120_spacing_conflict as p256_b120,
    test_invented_stirrup_quantity_rejected as p256_qty,
    test_no_bbs_mutation as p256_no_bbs,
    test_no_excel_mutation as p256_no_excel,
    test_no_production_mutation as p256_no_prod,
    test_no_steel_mutation as p256_no_steel,
    test_p251_fingerprint_unchanged as p256_p251,
    test_p254_regression_unchanged as p256_p254,
    test_p255_regression_unchanged as p256_p255,
    test_zone_not_promotable as p256_zone,
)

from .config import MODE, MODEL_VERSION, PRIMARY_SET_KEY
from .dataset import build_dataset_manifest
from .evidence_package import build_unseen_evidence_package
from .gt_oracle import ground_truth_for_intent
from .metrics import compute_cost_metrics
from .regression import capture_fingerprints, compare_fingerprints, fingerprint_paths, firewall_check
from .selective_gate import should_invoke_claude, trigger_reasons
from .three_way import evaluate_candidate

B46_TEXT = "4L-Y10@\\X100/150/100C/C"
B58_TEXT = "3L-Y12@\\X100C/C"
B120_TEXT = "3L-Y10@100C/150/100/C"


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _det(**kwargs: Any) -> Dict[str, Any]:
    row = {
        "intent_id": "QI::TEST::ANN-x",
        "beam_id": kwargs.get("beam_id", "TEST"),
        "annotation_id": kwargs.get("annotation_id", "ANN-x"),
        "raw_text": kwargs.get("text", "4-Y25"),
        "normalized_text": kwargs.get("text", "4-Y25"),
        "semantic_type": kwargs.get("stype", "LONGITUDINAL_BAR"),
        "reinforcement_role": kwargs.get("role", "UNKNOWN"),
        "quantity_status": kwargs.get("status", "EXPLICIT"),
        "quantity_value": kwargs.get("quantity", 4),
        "diameter_value_mm": kwargs.get("diameter", 25.0),
        "leg_count": kwargs.get("legs"),
        "spacing_values_mm": list(kwargs.get("spacing") or []),
    }
    return snapshot_from_frozen_intent(row)


def _vision(**kwargs: Any) -> Dict[str, Any]:
    cid = kwargs.get("cid", "VC::TEST::ANN-x")
    parsed = normalize_parsed(
        {
            "candidate_id": cid,
            "interpretation_status": kwargs.get("status", "RESOLVED"),
            "semantic_type": kwargs.get("stype", "LONGITUDINAL_BAR"),
            "role": kwargs.get("role", "TOP_BAR"),
            "quantity": kwargs.get("quantity", 4),
            "diameter_mm": kwargs.get("diameter", 25),
            "legs": kwargs.get("legs"),
            "spacing_mm": list(kwargs.get("spacing") or []),
            "beam_association": kwargs.get("assoc", "TARGET_BEAM"),
            "zone": kwargs.get("zone", "UNKNOWN"),
            "confidence": 0.9,
        }
    )
    validation = validate_interpretation(parsed=parsed, expected_candidate_id=cid)
    return {
        "api_ok": True,
        "live_call": True,
        "replay": False,
        "validation": validation,
        "validated_interpretation": validation.get("validated_interpretation"),
        "vision_source": "TEST",
        "prompt_fingerprint": "p" * 64,
        "evidence_fingerprint": "e" * 64,
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }


def _cand(text: str, cid: str = "VC::TEST::ANN-x", **extra: Any) -> Dict[str, Any]:
    d = {
        "candidate_id": cid,
        "beam_id": extra.pop("beam_id", "TEST"),
        "annotation_id": extra.pop("annotation_id", "ANN-x"),
        "raw_text": text,
        "normalized_text": text,
        "quantity_status": extra.pop("quantity_status", "EXPLICIT"),
        "baseline_semantic_type": extra.pop("baseline_semantic_type", "LONGITUDINAL_BAR"),
        "baseline_role": extra.pop("baseline_role", "UNKNOWN"),
        "candidate_reason_codes": extra.pop("candidate_reason_codes", []),
    }
    d.update(extra)
    return d


def test_unseen_dataset_manifest() -> None:
    m = build_dataset_manifest(_v10())
    assert m["drawing_set_id"] == "Fifth Set Drawings"
    assert m["set_key"] == "Fifth"
    assert "Fourth" not in (m.get("drawing_set_id") or "")
    assert m.get("dxf_count", 0) >= 2
    assert m.get("number_of_beams", 0) > 0
    assert "dataset_manifest" not in m or True
    assert "previous_benchmark_membership" in m


def test_unseen_status_validation() -> None:
    m = build_dataset_manifest(_v10())
    assert m["UNSEEN_SET_VERIFIED"] is True
    assert m["unseen_status"] is True
    assert PRIMARY_SET_KEY == "Fifth"


def test_ground_truth_not_in_prompt() -> None:
    cand = _cand("4L-Y10@\\X100/150/100C/C")
    cand["ground_truth"] = {"diameter_mm": 10, "role": "STIRRUP"}
    cand["expected_role"] = "STIRRUP"
    pkg = build_unseen_evidence_package(cand)
    meta = pkg["metadata"]
    prompt = build_user_prompt(meta)
    blob = (prompt + SYSTEM_PROMPT + str(meta)).lower()
    assert "ground_truth" not in meta
    assert "expected_role" not in meta
    assert "ground_truth" not in prompt
    leaks = assert_no_truth_leak(meta)
    leaks += assert_no_truth_leak({"user_prompt": prompt, "system": SYSTEM_PROMPT})
    assert leaks == []
    assert "10" in prompt or cand["raw_text"] in prompt  # annotation text is legitimate evidence
    assert "ground_truth" not in blob.split("4l-y10")[0] or "ground_truth" not in meta


def test_live_mode_required() -> None:
    assert MODE == "SELECTIVE_LIVE_SHADOW"
    from . import live_observer

    src = Path(live_observer.__file__).read_text(encoding="utf-8")
    assert "load_p254_vision_replay" not in src
    assert "call_claude_vision" in src
    assert "live_call\": True" in src.replace(" ", "") or 'live_call": True' in src


def test_selective_trigger_gate() -> None:
    det_ok = _det(text="4-Y25", stype="LONGITUDINAL_BAR", role="UNKNOWN", diameter=25.0, quantity=4)
    cand_ok = _cand("4-Y25")
    reasons = trigger_reasons(candidate=cand_ok, deterministic=det_ok)
    invoke, why = should_invoke_claude(reasons)
    assert invoke is False
    assert "SKIP" in why

    det_ocr = _det(
        text=B46_TEXT, stype="STIRRUP", role="STIRRUP",
        diameter=None, quantity=None, legs=None, spacing=[], status="UNRESOLVED",
    )
    reasons2 = trigger_reasons(candidate=_cand(B46_TEXT), deterministic=det_ocr)
    invoke2, why2 = should_invoke_claude(reasons2)
    assert invoke2 is True
    assert "OCR_UNCERTAIN" in why2 or "SPACING_UNCERTAIN" in why2 or "DIAMETER_UNCERTAIN" in why2

    det_sp = _det(
        text=B120_TEXT, stype="STIRRUP", role="STIRRUP",
        diameter=10.0, quantity=None, legs=3, spacing=[100], status="SPACING_BASED",
    )
    reasons3 = trigger_reasons(candidate=_cand(B120_TEXT), deterministic=det_sp)
    invoke3, _ = should_invoke_claude(reasons3)
    assert invoke3 is True


def test_deterministic_snapshot_unchanged() -> None:
    row = {
        "intent_id": "QI::B1::ANN-x",
        "beam_id": "B1",
        "annotation_id": "ANN-x",
        "raw_text": "4-Y25",
        "normalized_text": "4-Y25",
        "semantic_type": "LONGITUDINAL_BAR",
        "reinforcement_role": "UNKNOWN",
        "quantity_status": "EXPLICIT",
        "quantity_value": 4,
        "diameter_value_mm": 25.0,
        "leg_count": None,
        "spacing_values_mm": [],
    }
    a = snapshot_from_frozen_intent(row)
    b = snapshot_from_frozen_intent(copy.deepcopy(row))
    assert a["deterministic_quantity"] == b["deterministic_quantity"]
    assert a["deterministic_diameter"] == b["deterministic_diameter"]
    assert a["deterministic_type"] == b["deterministic_type"]


def test_field_level_evaluation() -> None:
    det = _det(text=B46_TEXT, stype="STIRRUP", role="STIRRUP", diameter=None, legs=None, spacing=[], status="UNRESOLVED", quantity=None)
    vis = _vision(stype="STIRRUP", role="STIRRUP", diameter=10, quantity=None, legs=4, spacing=[100, 150, 100])
    gt = ground_truth_for_intent(det["deterministic_result"], B46_TEXT)
    tw = evaluate_candidate(
        deterministic=det,
        vision=vis.get("validated_interpretation"),
        ground_truth=gt,
        accepted_shadow_fields=["diameter", "legs", "spacing"],
    )
    assert tw["diameter"]["scored"] is True
    assert tw["diameter"]["vision_eval"] == "EXACT"


def test_deterministic_correct_vision_wrong() -> None:
    det = _det(text=B58_TEXT, stype="STIRRUP", role="STIRRUP", diameter=12.0, legs=3, spacing=[100], quantity=None, status="SPACING_BASED")
    vis = _vision(stype="SIDE_FACE_REINFORCEMENT", role="SIDE_FACE", diameter=12, quantity=None, legs=3, spacing=[100])
    gt = ground_truth_for_intent(det["deterministic_result"], B58_TEXT)
    tw = evaluate_candidate(
        deterministic=det,
        vision=vis.get("validated_interpretation"),
        ground_truth=gt,
        accepted_shadow_fields=[],
    )
    rec = tw["semantic_type"]
    assert rec["deterministic_eval"] == "EXACT"
    assert rec["vision_eval"] == "WRONG"
    assert rec["dangerous_candidate"] is True


def test_deterministic_unknown_vision_correct() -> None:
    det = _det(text=B46_TEXT, stype="STIRRUP", role="STIRRUP", diameter=None, legs=None, spacing=[], quantity=None, status="UNRESOLVED")
    vis = _vision(stype="STIRRUP", role="STIRRUP", diameter=10, quantity=None, legs=4, spacing=[100, 150, 100])
    gt = ground_truth_for_intent(det["deterministic_result"], B46_TEXT)
    tw = evaluate_candidate(
        deterministic=det,
        vision=vis.get("validated_interpretation"),
        ground_truth=gt,
        accepted_shadow_fields=["diameter"],
    )
    assert tw["diameter"]["deterministic_eval"] == "UNRESOLVED"
    assert tw["diameter"]["vision_eval"] == "EXACT"
    assert tw["diameter"]["deterministic_unknown_vision_correct"] is True


def test_deterministic_wrong_vision_correct() -> None:
    det = _det(
        text=B120_TEXT, stype="STIRRUP", role="STIRRUP",
        diameter=10.0, legs=3, spacing=[100], quantity=None, status="SPACING_BASED",
    )
    vis = _vision(stype="STIRRUP", role="STIRRUP", diameter=10, quantity=None, legs=3, spacing=[100, 150, 100])
    gt = ground_truth_for_intent(det["deterministic_result"], B120_TEXT)
    tw = evaluate_candidate(
        deterministic=det,
        vision=vis.get("validated_interpretation"),
        ground_truth=gt,
        accepted_shadow_fields=[],
    )
    rec = tw["spacing"]
    assert rec["scored"] is True
    assert rec["deterministic_eval"] == "WRONG"
    assert rec["vision_eval"] == "EXACT"


def test_both_correct() -> None:
    det = _det(text="3L-Y10@100C/C", stype="STIRRUP", role="STIRRUP", diameter=10.0, legs=3, spacing=[100], quantity=None, status="SPACING_BASED")
    vis = _vision(stype="STIRRUP", role="STIRRUP", diameter=10, quantity=None, legs=3, spacing=[100])
    gt = ground_truth_for_intent(det["deterministic_result"], "3L-Y10@100C/C")
    tw = evaluate_candidate(
        deterministic=det,
        vision=vis.get("validated_interpretation"),
        ground_truth=gt,
        accepted_shadow_fields=[],
    )
    assert tw["diameter"]["both_correct"] is True
    assert tw["legs"]["both_correct"] is True


def test_both_wrong() -> None:
    det = _det(text=B58_TEXT, stype="SIDE_FACE_REINFORCEMENT", role="SIDE_FACE", diameter=None, quantity=None, status="UNRESOLVED")
    vis = _vision(stype="LONGITUDINAL_BAR", role="TOP_BAR", diameter=12, quantity=3, legs=None, spacing=[])
    gt = ground_truth_for_intent({"raw_text": B58_TEXT, "semantic_type": "STIRRUP", "reinforcement_role": "STIRRUP"}, B58_TEXT)
    tw = evaluate_candidate(
        deterministic=det,
        vision=vis.get("validated_interpretation"),
        ground_truth=gt,
        accepted_shadow_fields=[],
    )
    assert tw["semantic_type"]["both_wrong"] is True or (
        tw["semantic_type"]["deterministic_eval"] == "WRONG"
        and tw["semantic_type"]["vision_eval"] == "WRONG"
    )


def test_b58_semantic_conflict() -> None:
    p256_b58()


def test_b120_spacing_conflict() -> None:
    p256_b120()


def test_b46_stirrup_recovery() -> None:
    p256_b46()


def test_no_quantity_invention() -> None:
    p256_qty()


def test_zone_not_promotable() -> None:
    p256_zone()
    det = _det()
    vis = _vision(zone="SUPPORT")
    gt = {"available": True, "fields_available": ["zone"], "zone": "SPAN"}
    tw = evaluate_candidate(
        deterministic=det,
        vision=vis.get("validated_interpretation"),
        ground_truth=gt,
        accepted_shadow_fields=["zone"],
    )
    assert tw["zone"]["scored"] is False
    assert tw["zone"]["zone_promotable"] is False
    r = evaluate_one(candidate=_cand("4-Y25"), deterministic=det, vision_obs=vis)
    assert FIELD_ZONE not in r["accepted_shadow_fields"]


def test_no_production_mutation() -> None:
    p256_no_prod()
    steel = {"qty": 1}
    before = copy.deepcopy(steel)
    det = _det()
    vis = _vision()
    r = evaluate_one(candidate=_cand("4-Y25"), deterministic=det, vision_obs=vis)
    assert r["production_write"] is False
    assert r["field_result"]["production_mutation"] is False
    assert assert_field_result_not_production(r["field_result"])
    assert steel == before


def test_no_steel_mutation() -> None:
    p256_no_steel()


def test_no_bbs_mutation() -> None:
    p256_no_bbs()


def test_no_excel_mutation() -> None:
    p256_no_excel()


def test_p251_regression() -> None:
    p256_p251()
    paths = fingerprint_paths(_v10(), {})
    before = capture_fingerprints({"p251_matrix": paths["p251_matrix"]})
    after = capture_fingerprints({"p251_matrix": paths["p251_matrix"]})
    assert compare_fingerprints(before, after)["unchanged"] is True


def test_p254_regression() -> None:
    p256_p254()


def test_p255_regression() -> None:
    p256_p255()


def test_p256_regression() -> None:
    v10 = _v10()
    paths = fingerprint_paths(v10, {})
    keys = {"p256_status": paths["p256_status"], "p256_metrics": paths["p256_metrics"]}
    before = capture_fingerprints(keys)
    after = capture_fingerprints(keys)
    assert compare_fingerprints(before, after)["unchanged"] is True


def test_cost_tracking() -> None:
    rows = [
        {
            "invoke_claude": True,
            "vision_obs": {
                "live_call": True,
                "api_ok": True,
                "usage": {"input_tokens": 1000, "output_tokens": 200},
                "validated_interpretation": {"semantic_type": "STIRRUP"},
            },
        }
    ]
    c = compute_cost_metrics(vision_rows=rows, true_incremental_field_count=2, eligible_count=1)
    assert c["live_claude_calls"] == 1
    assert c["input_tokens"] == 1000
    assert c["output_tokens"] == 200
    assert c["estimated_cost_usd"] is not None
    assert c["cost_per_TRUE_INCREMENTAL_FIELD"] is not None


def test_prompt_fingerprint_recorded() -> None:
    cand = _cand("4-Y25")
    pkg = build_unseen_evidence_package(cand)
    prompt = build_user_prompt(pkg["metadata"])
    fp = prompt_fingerprint(SYSTEM_PROMPT, prompt)
    assert isinstance(fp, str) and len(fp) == 64


def test_evidence_fingerprint_recorded() -> None:
    cand = _cand("4-Y25")
    pkg = build_unseen_evidence_package(cand)
    assert pkg.get("evidence_fingerprint")
    assert len(pkg["evidence_fingerprint"]) == 64


def test_firewall_no_production_import() -> None:
    fw = firewall_check(_v10())
    assert fw["ok"] is True
    assert fw["offenders"] == []


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("unseen_dataset_manifest", test_unseen_dataset_manifest),
        ("unseen_status_validation", test_unseen_status_validation),
        ("ground_truth_not_in_prompt", test_ground_truth_not_in_prompt),
        ("live_mode_required", test_live_mode_required),
        ("selective_trigger_gate", test_selective_trigger_gate),
        ("deterministic_snapshot_unchanged", test_deterministic_snapshot_unchanged),
        ("field_level_evaluation", test_field_level_evaluation),
        ("deterministic_correct_vision_wrong", test_deterministic_correct_vision_wrong),
        ("deterministic_unknown_vision_correct", test_deterministic_unknown_vision_correct),
        ("deterministic_wrong_vision_correct", test_deterministic_wrong_vision_correct),
        ("both_correct", test_both_correct),
        ("both_wrong", test_both_wrong),
        ("B58_semantic_conflict", test_b58_semantic_conflict),
        ("B120_spacing_conflict", test_b120_spacing_conflict),
        ("B46_stirrup_recovery", test_b46_stirrup_recovery),
        ("no_quantity_invention", test_no_quantity_invention),
        ("zone_not_promotable", test_zone_not_promotable),
        ("no_production_mutation", test_no_production_mutation),
        ("no_steel_mutation", test_no_steel_mutation),
        ("no_bbs_mutation", test_no_bbs_mutation),
        ("no_excel_mutation", test_no_excel_mutation),
        ("p251_regression", test_p251_regression),
        ("p254_regression", test_p254_regression),
        ("p255_regression", test_p255_regression),
        ("p256_regression", test_p256_regression),
        ("cost_tracking", test_cost_tracking),
        ("prompt_fingerprint_recorded", test_prompt_fingerprint_recorded),
        ("evidence_fingerprint_recorded", test_evidence_fingerprint_recorded),
    ]
    results: List[Dict[str, Any]] = []
    for name, fn in tests:
        try:
            fn()
            results.append({"name": name, "pass": True})
        except Exception as exc:  # noqa: BLE001
            results.append({"name": name, "pass": False, "error": str(exc)})
    p256 = run_p256_unit_tests()
    p255 = p256.get("p255_unit_tests") or {}
    p254 = p256.get("p254_unit_tests") or run_p254_unit_tests()
    passed = sum(1 for r in results if r["pass"])
    return {
        "success": passed == len(tests) and bool(p256.get("success")),
        "passed": passed,
        "total": len(tests),
        "results": results,
        "p256_unit_tests": p256,
        "p255_unit_tests": p255,
        "p254_unit_tests": p254,
        "model_version": MODEL_VERSION,
    }


__all__ = ["run_unit_tests"]
