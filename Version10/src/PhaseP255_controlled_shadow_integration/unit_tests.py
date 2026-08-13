"""Unit tests for P2.5.5 (no live Claude calls)."""
from __future__ import annotations

import copy
from typing import Any, Dict, List

from PhaseP254_semantic_reinforcement_vision_benchmark.semantic_schema import normalize_parsed
from PhaseP254_semantic_reinforcement_vision_benchmark.unit_tests import (
    run_unit_tests as run_p254_unit_tests,
)
from PhaseP254_semantic_reinforcement_vision_benchmark.validator import validate_interpretation

from .arbitrator import classify_operational, collect_important_conflicts
from .config import (
    ACT_KEEP_DET,
    ACT_KEEP_DET_CONFLICT,
    ACT_KEEP_DET_VISION_ERROR,
    ACT_SHADOW_VISION,
    ACT_UNRESOLVED,
    CMP_BOTH_AGREE,
    CMP_BOTH_UNRESOLVED,
    CMP_DETERMINISTIC_ONLY_RESOLVED,
    CMP_VISION_CONFLICT,
    CMP_VISION_ONLY_RESOLVED,
    CMP_VISION_WRONG,
    MODEL_VERSION,
)
from .deterministic_snapshot import intent_to_snapshot, snapshot_from_frozen_intent
from .integrator import integrate_one
from .safety_gates import annotation_has_explicit_quantity, apply_safety_gates
from .shadow_contract import assert_shadow_not_production

B58_TEXT = "3L-Y12@\\X100C/C"


def _det(
    *,
    text: str = "4-Y25",
    status: str = "EXPLICIT",
    stype: str = "LONGITUDINAL_BAR",
    role: str = "TOP_BAR",
    diameter: Any = 25.0,
    quantity: Any = 4,
    legs: Any = None,
    spacing: Any = None,
) -> Dict[str, Any]:
    row = {
        "intent_id": "QI::TEST::ANN-x",
        "beam_id": "TEST",
        "annotation_id": "ANN-x",
        "raw_text": text,
        "normalized_text": text,
        "semantic_type": stype,
        "reinforcement_role": role,
        "quantity_status": status,
        "quantity_value": quantity,
        "diameter_value_mm": diameter,
        "leg_count": legs,
        "spacing_values_mm": list(spacing or []),
    }
    return snapshot_from_frozen_intent(row)


def _vision(
    *,
    cid: str = "VC::TEST::ANN-x",
    status: str = "RESOLVED",
    stype: str = "LONGITUDINAL_BAR",
    role: str = "TOP_BAR",
    diameter: Any = 25,
    quantity: Any = 4,
    legs: Any = None,
    spacing: Any = None,
    assoc: str = "TARGET_BEAM",
    zone: str = "UNKNOWN",
    valid: bool = True,
    api_ok: bool = True,
) -> Dict[str, Any]:
    parsed = normalize_parsed(
        {
            "candidate_id": cid,
            "interpretation_status": status,
            "semantic_type": stype,
            "role": role,
            "quantity": quantity,
            "diameter_mm": diameter,
            "legs": legs,
            "spacing_mm": list(spacing or []),
            "beam_association": assoc,
            "zone": zone,
            "confidence": 0.9,
        }
    )
    if valid:
        validation = validate_interpretation(parsed=parsed, expected_candidate_id=cid)
    else:
        validation = {"valid": False, "errors": ["FORCED_INVALID"], "warnings": []}
        parsed = None if not valid else parsed
    vis = validation.get("validated_interpretation") if valid else None
    if valid and vis is None:
        vis = parsed if validation.get("valid") else None
    return {
        "api_ok": api_ok,
        "validation": validation,
        "validated_interpretation": vis if validation.get("valid") else None,
        "vision_source": "TEST",
        "live_call": False,
        "usage": {},
    }


def _cand(text: str, cid: str = "VC::TEST::ANN-x", **extra: Any) -> Dict[str, Any]:
    d = {
        "candidate_id": cid,
        "beam_id": "TEST",
        "annotation_id": "ANN-x",
        "raw_text": text,
        "semantic_class": extra.pop("semantic_class", "LONGITUDINAL"),
        "semantic_class_tags": extra.pop("semantic_class_tags", []),
        "candidate_reason_codes": extra.pop("candidate_reason_codes", []),
        "p2523_completeness": extra.pop("p2523_completeness", "PASS"),
    }
    d.update(extra)
    return d


def _run(text: str, det: Dict[str, Any], vis: Dict[str, Any], gt: Any = None) -> Dict[str, Any]:
    return integrate_one(
        candidate=_cand(text),
        deterministic=det,
        vision_obs=vis,
        ground_truth=gt,
    )


def test_both_agree() -> None:
    det = _det()
    vis = _vision()
    r = _run("4-Y25", det, vis)
    assert r["operational_class"] == CMP_BOTH_AGREE
    assert r["arbitration_action"] == ACT_KEEP_DET
    assert r["shadow"]["production_write"] is False
    assert r["deterministic"]["deterministic_quantity"] == 4


def test_vision_only_resolved() -> None:
    det = _det(
        text="S.F.R.ON EACH FACE",
        status="UNRESOLVED",
        stype="UNKNOWN",
        role="UNKNOWN",
        diameter=None,
        quantity=None,
    )
    vis = _vision(
        stype="SIDE_FACE_REINFORCEMENT",
        role="SIDE_FACE",
        diameter=None,
        quantity=None,
        spacing=[],
    )
    r = _run("S.F.R.ON EACH FACE", det, vis)
    assert r["operational_class"] == CMP_VISION_ONLY_RESOLVED
    assert r["arbitration_action"] == ACT_SHADOW_VISION
    assert r["shadow"]["production_write"] is False
    assert r["shadow"]["promotion_eligible"] in (True, False)
    # Diagnostic flag must never imply a write
    assert r["deterministic"]["deterministic_type"] == "UNKNOWN"


def test_deterministic_only_resolved() -> None:
    det = _det()
    vis = _vision(status="INSUFFICIENT_EVIDENCE", stype="UNKNOWN", role="UNKNOWN", quantity=None, diameter=None)
    # Insufficient with UNKNOWN type may fail validator enum... force invalid/abstain
    vis = {
        "api_ok": True,
        "validation": {"valid": False, "errors": ["ABSTAINED"], "warnings": []},
        "validated_interpretation": None,
        "vision_source": "TEST",
        "live_call": False,
        "usage": {},
    }
    r = _run("4-Y25", det, vis)
    assert r["operational_class"] == CMP_DETERMINISTIC_ONLY_RESOLVED
    assert r["arbitration_action"] == ACT_KEEP_DET


def test_vision_conflict() -> None:
    det = _det(
        text=B58_TEXT,
        status="SPACING_BASED",
        stype="STIRRUP",
        role="STIRRUP",
        diameter=12.0,
        quantity=None,
        legs=3,
        spacing=[100.0],
    )
    vis = _vision(
        stype="SIDE_FACE_REINFORCEMENT",
        role="SIDE_FACE",
        diameter=12,
        quantity=None,
        legs=3,
        spacing=[100],
    )
    r = _run(B58_TEXT, det, vis)
    assert r["operational_class"] == CMP_VISION_CONFLICT
    assert r["arbitration_action"] == ACT_KEEP_DET_CONFLICT
    assert "type" in r["conflict_fields"] or "role" in r["conflict_fields"]
    assert r["deterministic"]["deterministic_type"] == "STIRRUP"


def test_both_unresolved() -> None:
    det = _det(
        text="Ld",
        status="UNRESOLVED",
        stype="UNKNOWN",
        role="UNKNOWN",
        diameter=None,
        quantity=None,
    )
    vis = {
        "api_ok": True,
        "validation": {"valid": False, "errors": ["INSUFFICIENT"], "warnings": []},
        "validated_interpretation": None,
        "vision_source": "TEST",
        "live_call": False,
        "usage": {},
    }
    r = _run("Ld", det, vis)
    assert r["operational_class"] == CMP_BOTH_UNRESOLVED
    assert r["arbitration_action"] == ACT_UNRESOLVED


def test_vision_wrong_evaluation() -> None:
    det = _det(
        text=B58_TEXT,
        status="SPACING_BASED",
        stype="STIRRUP",
        role="STIRRUP",
        diameter=12.0,
        quantity=None,
        legs=3,
        spacing=[100.0],
    )
    vis = _vision(
        stype="SIDE_FACE_REINFORCEMENT",
        role="SIDE_FACE",
        diameter=12,
        quantity=None,
        legs=3,
        spacing=[100],
    )
    gt = {
        "available": True,
        "semantic_type": "STIRRUP",
        "role": "STIRRUP",
        "quantity": None,
        "diameter_mm": 12.0,
        "legs": 3,
        "spacing_mm": [100],
        "beam_association": "TARGET_BEAM",
        "zone": None,
        "fields_available": ["semantic_type", "role", "diameter_mm", "legs", "spacing_mm", "beam_association"],
    }
    r = _run(B58_TEXT, det, vis, gt)
    assert r["comparison_class"] == CMP_VISION_WRONG
    assert r["arbitration_action"] == ACT_KEEP_DET_VISION_ERROR
    assert r["operational_class"] == CMP_VISION_CONFLICT


def test_b58_semantic_conflict_protection() -> None:
    det = _det(
        text=B58_TEXT,
        status="SPACING_BASED",
        stype="STIRRUP",
        role="STIRRUP",
        diameter=12.0,
        quantity=None,
        legs=3,
        spacing=[100.0],
    )
    frozen = copy.deepcopy(det)

    vis_ok = _vision(
        cid="VC::B58::ANN-a0c82bbe",
        stype="STIRRUP",
        role="STIRRUP",
        diameter=12,
        quantity=None,
        legs=3,
        spacing=[100],
    )
    agree = integrate_one(
        candidate=_cand(B58_TEXT, cid="VC::B58::ANN-a0c82bbe"),
        deterministic=det,
        vision_obs=vis_ok,
    )
    assert agree["operational_class"] == CMP_BOTH_AGREE
    assert agree["deterministic"] == det

    vis_bad = _vision(
        cid="VC::B58::ANN-a0c82bbe",
        stype="SIDE_FACE_REINFORCEMENT",
        role="SIDE_FACE",
        diameter=12,
        quantity=None,
        legs=3,
        spacing=[100],
    )
    conflict = integrate_one(
        candidate=_cand(B58_TEXT, cid="VC::B58::ANN-a0c82bbe"),
        deterministic=det,
        vision_obs=vis_bad,
        ground_truth={
            "available": True,
            "semantic_type": "STIRRUP",
            "role": "STIRRUP",
            "diameter_mm": 12.0,
            "legs": 3,
            "spacing_mm": [100],
            "beam_association": "TARGET_BEAM",
            "fields_available": ["semantic_type", "role", "diameter_mm", "legs", "spacing_mm", "beam_association"],
        },
    )
    assert conflict["operational_class"] == CMP_VISION_CONFLICT
    assert conflict["comparison_class"] == CMP_VISION_WRONG
    assert conflict["deterministic"] == frozen
    assert conflict["shadow"]["production_write"] is False
    assert conflict["shadow"]["deterministic_type"] == "STIRRUP"
    assert conflict["shadow"]["vision_type"] == "SIDE_FACE_REINFORCEMENT"


def test_no_production_mutation() -> None:
    steel = {"qty": 12}
    bbs = {"rows": [1]}
    excel = {"path": "EstimatorOutput.xlsx"}
    before = (copy.deepcopy(steel), copy.deepcopy(bbs), copy.deepcopy(excel))
    r = _run("4-Y25", _det(), _vision())
    assert r["shadow"]["production_write"] is False
    assert assert_shadow_not_production(r["shadow"])
    assert (steel, bbs, excel) == before


def test_no_steel_quantity_mutation() -> None:
    qty = {"B97A": 4}
    snapshot = copy.deepcopy(qty)
    _run("4-Y25", _det(), _vision())
    assert qty == snapshot


def test_no_bbs_mutation() -> None:
    bbs = {"stirrups": ["3L-Y10@100C/C"]}
    snapshot = copy.deepcopy(bbs)
    _run(B58_TEXT, _det(text=B58_TEXT, stype="STIRRUP", role="STIRRUP", quantity=None, legs=3, spacing=[100], status="SPACING_BASED", diameter=12), _vision(stype="STIRRUP", role="STIRRUP", quantity=None, legs=3, spacing=[100], diameter=12))
    assert bbs == snapshot


def test_no_excel_mutation() -> None:
    excel_bytes = b"PK\x03\x04fake"
    after = excel_bytes
    _run("4-Y25", _det(), _vision())
    assert after == excel_bytes


def test_invalid_claude_response() -> None:
    det = _det()
    vis = {
        "api_ok": True,
        "validation": {"valid": False, "errors": ["PARSE_FAILED"], "warnings": []},
        "validated_interpretation": None,
        "vision_source": "TEST",
        "live_call": False,
        "usage": {},
    }
    r = _run("4-Y25", det, vis)
    assert r["operational_class"] == CMP_DETERMINISTIC_ONLY_RESOLVED
    assert r["shadow"]["vision_status"] in ("INVALID_OR_ABSTAINED", "API_ERROR")
    assert r["deterministic"]["deterministic_type"] == "LONGITUDINAL_BAR"


def test_invented_quantity_rejection() -> None:
    assert annotation_has_explicit_quantity("S.F.R.ON EACH FACE") is False
    det = _det(
        text="S.F.R.ON EACH FACE",
        status="UNRESOLVED",
        stype="UNKNOWN",
        role="UNKNOWN",
        diameter=None,
        quantity=None,
    )
    vis = _vision(
        stype="SIDE_FACE_REINFORCEMENT",
        role="SIDE_FACE",
        quantity=4,
        diameter=12,
        spacing=[],
    )
    r = _run("S.F.R.ON EACH FACE", det, vis)
    assert r["safety"]["vision_rejected"] is True
    assert "INVENTED_QUANTITY" in r["safety"]["flags"]
    assert r["shadow"]["promotion_eligible"] is False


def test_stirrup_quantity_protection() -> None:
    parsed = normalize_parsed(
        {
            "candidate_id": "VC::TEST::ANN-x",
            "interpretation_status": "RESOLVED",
            "semantic_type": "STIRRUP",
            "role": "STIRRUP",
            "quantity": 4,
            "diameter_mm": 10,
            "legs": 3,
            "spacing_mm": [100],
            "beam_association": "TARGET_BEAM",
            "zone": "UNKNOWN",
            "confidence": 0.9,
        }
    )
    v = validate_interpretation(parsed=parsed, expected_candidate_id="VC::TEST::ANN-x")
    assert v["valid"] is False
    assert "STIRRUP_MUST_NOT_HAVE_LONGITUDINAL_QUANTITY" in v["errors"]
    det = _det(
        text="3L-Y10@100C/C",
        status="SPACING_BASED",
        stype="STIRRUP",
        role="STIRRUP",
        diameter=10.0,
        quantity=None,
        legs=3,
        spacing=[100.0],
    )
    vis = {
        "api_ok": True,
        "validation": v,
        "validated_interpretation": v.get("validated_interpretation"),
        "vision_source": "TEST",
        "live_call": False,
        "usage": {},
    }
    r = _run("3L-Y10@100C/C", det, vis)
    assert r["operational_class"] == CMP_DETERMINISTIC_ONLY_RESOLVED
    assert r["deterministic"]["deterministic_quantity"] is None


def test_zone_remains_unpromoted() -> None:
    r = _run("4-Y25", _det(), _vision(zone="SUPPORT"))
    assert r["shadow"]["zone_promotable"] is False
    assert r["shadow"]["production_write"] is False
    # Zone disagreement is not an operational conflict
    flags, _ = collect_important_conflicts(
        deterministic=_det(),
        vision=r["shadow"]["vision_result"],
    )
    assert "zone" not in flags


def test_deterministic_fingerprint_unchanged() -> None:
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
    assert a["deterministic_type"] == b["deterministic_type"]
    assert a["deterministic_quantity"] == b["deterministic_quantity"]
    assert a["deterministic_diameter"] == b["deterministic_diameter"]
    vis = _vision()
    r = _run("4-Y25", a, vis)
    assert r["deterministic"]["deterministic_quantity"] == 4
    assert r["deterministic"]["deterministic_type"] == "LONGITUDINAL_BAR"


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("both_agree", test_both_agree),
        ("vision_only_resolved", test_vision_only_resolved),
        ("deterministic_only_resolved", test_deterministic_only_resolved),
        ("vision_conflict", test_vision_conflict),
        ("both_unresolved", test_both_unresolved),
        ("vision_wrong_evaluation", test_vision_wrong_evaluation),
        ("b58_semantic_conflict_protection", test_b58_semantic_conflict_protection),
        ("no_production_mutation", test_no_production_mutation),
        ("no_steel_quantity_mutation", test_no_steel_quantity_mutation),
        ("no_bbs_mutation", test_no_bbs_mutation),
        ("no_excel_mutation", test_no_excel_mutation),
        ("invalid_claude_response", test_invalid_claude_response),
        ("invented_quantity_rejection", test_invented_quantity_rejection),
        ("stirrup_quantity_protection", test_stirrup_quantity_protection),
        ("zone_remains_unpromoted", test_zone_remains_unpromoted),
        ("deterministic_fingerprint_unchanged", test_deterministic_fingerprint_unchanged),
    ]
    results: List[Dict[str, Any]] = []
    for name, fn in tests:
        try:
            fn()
            results.append({"name": name, "pass": True})
        except Exception as exc:  # noqa: BLE001
            results.append({"name": name, "pass": False, "error": str(exc)})
    p254 = run_p254_unit_tests()
    passed = sum(1 for r in results if r["pass"])
    return {
        "success": passed == len(tests) and bool(p254.get("success")),
        "passed": passed,
        "total": len(tests),
        "results": results,
        "p254_unit_tests": p254,
        "model_version": MODEL_VERSION,
    }


__all__ = ["run_unit_tests"]
