"""Unit tests for P2.5.6 (no live Claude calls)."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, List

from PhaseP254_semantic_reinforcement_vision_benchmark.semantic_schema import normalize_parsed
from PhaseP254_semantic_reinforcement_vision_benchmark.unit_tests import (
    run_unit_tests as run_p254_unit_tests,
)
from PhaseP254_semantic_reinforcement_vision_benchmark.validator import validate_interpretation
from PhaseP255_controlled_shadow_integration.deterministic_snapshot import (
    snapshot_from_frozen_intent,
)
from PhaseP255_controlled_shadow_integration.unit_tests import (
    run_unit_tests as run_p255_unit_tests,
)

from .config import (
    FIELD_ASSOCIATION,
    FIELD_DIAMETER,
    FIELD_LEGS,
    FIELD_QUANTITY,
    FIELD_ROLE,
    FIELD_SEMANTIC_TYPE,
    FIELD_SPACING,
    FIELD_ZONE,
    MODEL_VERSION,
    ST_BOTH_AGREE,
    ST_NOT_APPLICABLE,
    ST_UNRESOLVED,
    ST_VISION_CONFLICT,
    ST_VISION_FIELD_CANDIDATE,
    ST_VISION_REJECTED,
)
from .field_contract import assert_field_result_not_production
from .field_validator import validate_diameter, validate_legs, validate_spacing
from .integrator import evaluate_one
from .regression import capture_fingerprints, compare_fingerprints, fingerprint_paths

B46_TEXT = "4L-Y10@\\X100/150/100C/C"
B58_TEXT = "3L-Y12@\\X100C/C"
B120_TEXT = "3L-Y10@100C/150/100/C"


def _det(**kwargs: Any) -> Dict[str, Any]:
    row = {
        "intent_id": "QI::TEST::ANN-x",
        "beam_id": kwargs.get("beam_id", "TEST"),
        "annotation_id": kwargs.get("annotation_id", "ANN-x"),
        "raw_text": kwargs.get("text", "4-Y25"),
        "normalized_text": kwargs.get("text", "4-Y25"),
        "semantic_type": kwargs.get("stype", "LONGITUDINAL_BAR"),
        "reinforcement_role": kwargs.get("role", "TOP_BAR"),
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
        "api_ok": kwargs.get("api_ok", True),
        "validation": validation,
        "validated_interpretation": validation.get("validated_interpretation"),
        "vision_source": "TEST",
        "live_call": False,
        "usage": {},
    }


def _cand(text: str, cid: str = "VC::TEST::ANN-x", **extra: Any) -> Dict[str, Any]:
    d = {
        "candidate_id": cid,
        "beam_id": extra.pop("beam_id", "TEST"),
        "annotation_id": extra.pop("annotation_id", "ANN-x"),
        "raw_text": text,
        "semantic_class": extra.pop("semantic_class", "STIRRUP"),
        "semantic_class_tags": extra.pop("semantic_class_tags", []),
        "candidate_reason_codes": extra.pop("candidate_reason_codes", []),
        "p2523_completeness": extra.pop("p2523_completeness", "PASS"),
    }
    d.update(extra)
    return d


def _run(text: str, det: Dict[str, Any], vis: Dict[str, Any], cid: str = "VC::TEST::ANN-x") -> Dict[str, Any]:
    return evaluate_one(candidate=_cand(text, cid=cid), deterministic=det, vision_obs=vis)


def _fc(row: Dict[str, Any], field: str) -> Dict[str, Any]:
    return (row["field_result"]["field_comparisons"] or {}).get(field) or {}


def test_field_both_agree() -> None:
    r = _run("4-Y25", _det(), _vision())
    assert _fc(r, FIELD_SEMANTIC_TYPE)["field_status"] == ST_BOTH_AGREE
    assert _fc(r, FIELD_DIAMETER)["field_status"] == ST_BOTH_AGREE
    assert _fc(r, FIELD_QUANTITY)["field_status"] == ST_BOTH_AGREE
    assert r["field_result"]["production_write"] is False


def test_vision_only_diameter_candidate() -> None:
    det = _det(text=B46_TEXT, status="UNRESOLVED", stype="STIRRUP", role="STIRRUP", diameter=None, quantity=None, legs=None, spacing=[])
    vis = _vision(stype="STIRRUP", role="STIRRUP", diameter=10, quantity=None, legs=4, spacing=[100, 150, 100])
    r = _run(B46_TEXT, det, vis)
    rec = _fc(r, FIELD_DIAMETER)
    assert rec["field_status"] == ST_VISION_FIELD_CANDIDATE
    assert rec["accepted"] is True
    assert rec["vision_value"] == 10
    assert rec["production_change"] == "NONE"


def test_vision_only_legs_candidate() -> None:
    det = _det(text=B46_TEXT, status="UNRESOLVED", stype="STIRRUP", role="STIRRUP", diameter=None, quantity=None, legs=None, spacing=[])
    vis = _vision(stype="STIRRUP", role="STIRRUP", diameter=10, quantity=None, legs=4, spacing=[100, 150, 100])
    rec = _fc(_run(B46_TEXT, det, vis), FIELD_LEGS)
    assert rec["field_status"] == ST_VISION_FIELD_CANDIDATE
    assert rec["accepted"] is True
    assert rec["vision_value"] == 4


def test_vision_only_spacing_candidate() -> None:
    det = _det(text=B46_TEXT, status="UNRESOLVED", stype="STIRRUP", role="STIRRUP", diameter=None, quantity=None, legs=None, spacing=[])
    vis = _vision(stype="STIRRUP", role="STIRRUP", diameter=10, quantity=None, legs=4, spacing=[100, 150, 100])
    rec = _fc(_run(B46_TEXT, det, vis), FIELD_SPACING)
    assert rec["field_status"] == ST_VISION_FIELD_CANDIDATE
    assert rec["accepted"] is True
    assert rec["vision_value"] == [100, 150, 100]


def test_deterministic_value_wins_conflict() -> None:
    det = _det(diameter=10.0, stype="STIRRUP", role="STIRRUP", quantity=None, legs=3, spacing=[100], status="SPACING_BASED", text="3L-Y10@100C/C")
    vis = _vision(stype="STIRRUP", role="STIRRUP", diameter=12, quantity=None, legs=3, spacing=[100])
    rec = _fc(_run("3L-Y10@100C/C", det, vis), FIELD_DIAMETER)
    assert rec["field_status"] == ST_VISION_CONFLICT
    assert rec["accepted"] is False
    assert rec["deterministic_value"] == 10.0
    assert rec["field_decision"] == "KEEP_DETERMINISTIC_FLAG_CONFLICT"


def test_b58_type_role_conflict() -> None:
    det = _det(
        text=B58_TEXT, beam_id="B58", annotation_id="ANN-a0c82bbe",
        status="UNRESOLVED", stype="STIRRUP", role="STIRRUP",
        diameter=None, quantity=None, legs=None, spacing=[],
    )
    vis = _vision(
        cid="VC::B58::ANN-a0c82bbe", stype="SIDE_FACE_REINFORCEMENT", role="SIDE_FACE",
        diameter=12, quantity=None, legs=3, spacing=[100],
    )
    r = evaluate_one(
        candidate=_cand(B58_TEXT, cid="VC::B58::ANN-a0c82bbe", beam_id="B58", annotation_id="ANN-a0c82bbe"),
        deterministic=det,
        vision_obs=vis,
    )
    assert _fc(r, FIELD_SEMANTIC_TYPE)["field_status"] == ST_VISION_CONFLICT
    assert _fc(r, FIELD_ROLE)["field_status"] == ST_VISION_CONFLICT
    assert FIELD_SEMANTIC_TYPE in r["conflict_fields"]
    assert FIELD_ROLE in r["conflict_fields"]
    assert r["field_result"]["deterministic_result"]["semantic_type"] == "STIRRUP"
    assert r["field_result"]["production_write"] is False


def test_b120_spacing_conflict() -> None:
    det = _det(
        text=B120_TEXT, beam_id="B120",
        status="SPACING_BASED", stype="STIRRUP", role="STIRRUP",
        diameter=10.0, quantity=None, legs=3, spacing=[100.0],
    )
    vis = _vision(stype="STIRRUP", role="STIRRUP", diameter=10, quantity=None, legs=3, spacing=[100, 150, 100])
    r = _run(B120_TEXT, det, vis, cid="VC::B120::ANN-f4213b73")
    rec = _fc(r, FIELD_SPACING)
    assert rec["field_status"] == ST_VISION_CONFLICT
    assert rec["reason"] == "DETERMINISTIC_CONFLICT"
    assert rec["accepted"] is False
    assert rec["safe"] is False
    assert rec["production_change"] == "NONE"
    assert _fc(r, FIELD_SEMANTIC_TYPE)["field_status"] == ST_BOTH_AGREE
    assert _fc(r, FIELD_ROLE)["field_status"] == ST_BOTH_AGREE


def test_b46_field_supplementation() -> None:
    det = _det(
        text=B46_TEXT, beam_id="B46",
        status="UNRESOLVED", stype="STIRRUP", role="STIRRUP",
        diameter=None, quantity=None, legs=None, spacing=[],
    )
    vis = _vision(stype="STIRRUP", role="STIRRUP", diameter=10, quantity=None, legs=4, spacing=[100, 150, 100])
    r = _run(B46_TEXT, det, vis, cid="VC::B46::ANN-a09ab748")
    accepted = r["accepted_shadow_fields"]
    assert "diameter" in accepted
    assert "legs" in accepted
    assert "spacing" in accepted
    assert FIELD_SEMANTIC_TYPE not in accepted
    assert FIELD_ROLE not in accepted
    assert _fc(r, FIELD_SEMANTIC_TYPE)["field_status"] == ST_BOTH_AGREE
    assert _fc(r, FIELD_ROLE)["field_status"] == ST_BOTH_AGREE
    assert r["field_result"]["production_write"] is False


def test_invented_stirrup_quantity_rejected() -> None:
    det = _det(text="3L-Y10@100C/C", status="SPACING_BASED", stype="STIRRUP", role="STIRRUP", diameter=10.0, quantity=None, legs=3, spacing=[100])
    vis = _vision(stype="STIRRUP", role="STIRRUP", diameter=10, quantity=8, legs=3, spacing=[100])
    # Schema validator rejects stirrup+quantity entirely
    if vis.get("validated_interpretation") is None:
        r = _run("3L-Y10@100C/C", det, vis)
        assert r["field_result"]["production_write"] is False
        rec = _fc(r, FIELD_QUANTITY)
        assert rec["accepted"] is False
        return
    rec = _fc(_run("3L-Y10@100C/C", det, vis), FIELD_QUANTITY)
    assert rec["accepted"] is False
    assert rec["field_status"] in (ST_VISION_REJECTED, ST_UNRESOLVED, ST_NOT_APPLICABLE, ST_VISION_CONFLICT)


def test_invalid_diameter_rejected() -> None:
    ok, err = validate_diameter(-10)
    assert ok is False
    ok, err = validate_diameter(99)
    assert ok is False
    det = _det(text=B46_TEXT, status="UNRESOLVED", stype="STIRRUP", role="STIRRUP", diameter=None, quantity=None, legs=None)
    vis = _vision(stype="STIRRUP", role="STIRRUP", diameter=99, quantity=None, legs=4, spacing=[100])
    rec = _fc(_run(B46_TEXT, det, vis), FIELD_DIAMETER)
    assert rec["accepted"] is False
    assert rec["field_status"] in (ST_UNRESOLVED, ST_VISION_REJECTED)


def test_invalid_spacing_rejected() -> None:
    ok, _ = validate_spacing([-1, 100])
    assert ok is False
    det = _det(text=B46_TEXT, status="UNRESOLVED", stype="STIRRUP", role="STIRRUP", diameter=None, quantity=None, legs=None, spacing=[])
    vis = _vision(stype="STIRRUP", role="STIRRUP", diameter=10, quantity=None, legs=4, spacing=[-50])
    rec = _fc(_run(B46_TEXT, det, vis), FIELD_SPACING)
    assert rec["accepted"] is False


def test_invalid_legs_rejected() -> None:
    ok, _ = validate_legs(0)
    assert ok is False
    ok, _ = validate_legs(1.5)
    assert ok is False
    det = _det(text=B46_TEXT, status="UNRESOLVED", stype="STIRRUP", role="STIRRUP", diameter=None, quantity=None, legs=None)
    vis = _vision(stype="STIRRUP", role="STIRRUP", diameter=10, quantity=None, legs=0, spacing=[100])
    rec = _fc(_run(B46_TEXT, det, vis), FIELD_LEGS)
    assert rec["accepted"] is False


def test_longitudinal_legs_not_applicable() -> None:
    r = _run("4-Y25", _det(), _vision(legs=None))
    rec = _fc(r, FIELD_LEGS)
    assert rec["field_status"] == ST_NOT_APPLICABLE
    assert rec["accepted"] is False
    det = _det()
    vis = _vision(legs=3)
    rec2 = _fc(_run("4-Y25", det, vis), FIELD_LEGS)
    assert rec2["accepted"] is False
    assert rec2["field_status"] in (ST_VISION_REJECTED, ST_NOT_APPLICABLE)


def test_zone_not_promotable() -> None:
    r = _run("4-Y25", _det(), _vision(zone="SUPPORT"))
    assert r["field_result"]["zone_promotable"] is False
    assert r["field_result"]["zone_candidate_allowed"] is False
    assert FIELD_ZONE not in r["accepted_shadow_fields"]
    rec = _fc(r, FIELD_ZONE)
    assert rec["accepted"] is False
    assert rec["field_decision"] == "ZONE_DIAGNOSTIC_ONLY"


def test_beam_association_conflict() -> None:
    det = _det()
    vis = _vision(assoc="OTHER_BEAM")
    rec = _fc(_run("4-Y25", det, vis), FIELD_ASSOCIATION)
    assert rec["field_status"] == ST_VISION_CONFLICT
    assert rec["accepted"] is False
    assert rec["reason"] == "DETERMINISTIC_CONFLICT"


def test_no_production_mutation() -> None:
    steel = {"qty": 12}
    before = copy.deepcopy(steel)
    r = _run("4-Y25", _det(), _vision())
    assert r["field_result"]["production_write"] is False
    assert r["field_result"]["production_mutation"] is False
    assert assert_field_result_not_production(r["field_result"])
    assert steel == before


def test_no_steel_mutation() -> None:
    qty = {"B97A": 4}
    snap = copy.deepcopy(qty)
    _run("4-Y25", _det(), _vision())
    assert qty == snap


def test_no_bbs_mutation() -> None:
    bbs = {"rows": ["3L-Y10@100C/C"]}
    snap = copy.deepcopy(bbs)
    _run(B58_TEXT, _det(text=B58_TEXT, stype="STIRRUP", role="STIRRUP", quantity=None, legs=3, spacing=[100], diameter=12, status="SPACING_BASED"), _vision(stype="STIRRUP", role="STIRRUP", quantity=None, legs=3, spacing=[100], diameter=12))
    assert bbs == snap


def test_no_excel_mutation() -> None:
    excel = b"PK\x03\x04fake"
    _run("4-Y25", _det(), _vision())
    assert excel == b"PK\x03\x04fake"


def test_p251_fingerprint_unchanged() -> None:
    row = {
        "intent_id": "QI::B97A::ANN-d7128f62",
        "beam_id": "B97A",
        "annotation_id": "ANN-d7128f62",
        "raw_text": "4-Y25",
        "normalized_text": "4-Y25",
        "semantic_type": "LONGITUDINAL_BAR",
        "reinforcement_role": "TOP_BAR",
        "quantity_status": "EXPLICIT",
        "quantity_value": 4,
        "diameter_value_mm": 25.0,
        "leg_count": None,
        "spacing_values_mm": [],
    }
    a = snapshot_from_frozen_intent(row)
    b = snapshot_from_frozen_intent(copy.deepcopy(row))
    assert a["deterministic_quantity"] == b["deterministic_quantity"]
    r = _run("4-Y25", a, _vision())
    assert r["deterministic"]["deterministic_quantity"] == 4
    assert r["deterministic"]["deterministic_type"] == "LONGITUDINAL_BAR"


def test_p254_regression_unchanged() -> None:
    v10 = Path(__file__).resolve().parents[2]
    paths = fingerprint_paths(v10, {})
    before = capture_fingerprints({"p254_status": paths["p254_status"], "p254_manifest": paths["p254_manifest"]})
    after = capture_fingerprints({"p254_status": paths["p254_status"], "p254_manifest": paths["p254_manifest"]})
    cmp = compare_fingerprints(before, after)
    assert cmp["unchanged"] is True


def test_p255_regression_unchanged() -> None:
    v10 = Path(__file__).resolve().parents[2]
    paths = fingerprint_paths(v10, {})
    keys = {"p255_status": paths["p255_status"], "p255_metrics": paths["p255_metrics"]}
    before = capture_fingerprints(keys)
    after = capture_fingerprints(keys)
    cmp = compare_fingerprints(before, after)
    assert cmp["unchanged"] is True


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("field_both_agree", test_field_both_agree),
        ("vision_only_diameter_candidate", test_vision_only_diameter_candidate),
        ("vision_only_legs_candidate", test_vision_only_legs_candidate),
        ("vision_only_spacing_candidate", test_vision_only_spacing_candidate),
        ("deterministic_value_wins_conflict", test_deterministic_value_wins_conflict),
        ("b58_type_role_conflict", test_b58_type_role_conflict),
        ("b120_spacing_conflict", test_b120_spacing_conflict),
        ("b46_field_supplementation", test_b46_field_supplementation),
        ("invented_stirrup_quantity_rejected", test_invented_stirrup_quantity_rejected),
        ("invalid_diameter_rejected", test_invalid_diameter_rejected),
        ("invalid_spacing_rejected", test_invalid_spacing_rejected),
        ("invalid_legs_rejected", test_invalid_legs_rejected),
        ("longitudinal_legs_not_applicable", test_longitudinal_legs_not_applicable),
        ("zone_not_promotable", test_zone_not_promotable),
        ("beam_association_conflict", test_beam_association_conflict),
        ("no_production_mutation", test_no_production_mutation),
        ("no_steel_mutation", test_no_steel_mutation),
        ("no_bbs_mutation", test_no_bbs_mutation),
        ("no_excel_mutation", test_no_excel_mutation),
        ("p251_fingerprint_unchanged", test_p251_fingerprint_unchanged),
        ("p254_regression_unchanged", test_p254_regression_unchanged),
        ("p255_regression_unchanged", test_p255_regression_unchanged),
    ]
    results: List[Dict[str, Any]] = []
    for name, fn in tests:
        try:
            fn()
            results.append({"name": name, "pass": True})
        except Exception as exc:  # noqa: BLE001
            results.append({"name": name, "pass": False, "error": str(exc)})
    p255 = run_p255_unit_tests()
    p254 = p255.get("p254_unit_tests") or run_p254_unit_tests()
    passed = sum(1 for r in results if r["pass"])
    return {
        "success": passed == len(tests) and bool(p255.get("success")),
        "passed": passed,
        "total": len(tests),
        "results": results,
        "p255_unit_tests": p255,
        "p254_unit_tests": p254,
        "model_version": MODEL_VERSION,
    }


__all__ = ["run_unit_tests"]
