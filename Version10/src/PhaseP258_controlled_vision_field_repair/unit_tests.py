"""Unit tests for P2.5.8 (default: no live Claude calls)."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, List

from PhaseP257_unseen_drawing_controlled_vision_validation.unit_tests import (
    run_unit_tests as run_p257_unit_tests,
    test_p251_regression as p257_p251,
    test_p254_regression as p257_p254,
    test_p255_regression as p257_p255,
    test_p256_regression as p257_p256,
)

from .comparison import beam_improvement
from .config import MODEL_VERSION
from .det_status import classify_deterministic_status
from .metrics import steel_accuracy_pct
from .promotion_gate import evaluate_audit, evaluate_field_promotion
from .promotion_rules import is_whitelisted, load_promotion_rules
from .r13_overlay import apply_repairs
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
)

B46_TEXT = "4L-Y10@\\X100/150/100C/C"
B58_TEXT = "3L-Y12@\\X100C/C"
B120_TEXT = "3L-Y10@100C/150/100/C"


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _audit(
    *,
    text: str,
    beam_id: str,
    stype: str = "STIRRUP",
    role: str = "STIRRUP",
    diameter: Any = None,
    legs: Any = None,
    spacing: Any = None,
    vis_type: str = "STIRRUP",
    vis_role: str = "STIRRUP",
    vis_diameter: Any = None,
    vis_legs: Any = None,
    vis_spacing: Any = None,
    vis_qty: Any = None,
    tw: Any = None,
    cid: str = "VC::TEST::ANN-x",
) -> Dict[str, Any]:
    spacing = list(spacing or [])
    vis_spacing = list(vis_spacing or [])
    return {
        "candidate_id": cid,
        "beam_id": beam_id,
        "annotation_id": "ANN-x",
        "annotation_text": text,
        "invoke_claude": True,
        "shadow_trigger_reason": ["OCR_CORRUPTION"] if "\\X" in text else ["INCOMPLETE_SPACING"],
        "deterministic_result": {
            "semantic_type": stype,
            "reinforcement_role": role,
            "diameter_value_mm": diameter,
            "leg_count": legs,
            "spacing_values_mm": spacing,
            "quantity_value": None,
        },
        "vision_result": {
            "semantic_type": vis_type,
            "role": vis_role,
            "diameter_mm": vis_diameter,
            "legs": vis_legs,
            "spacing_mm": vis_spacing,
            "quantity": vis_qty,
            "zone": "SPAN",
        },
        "three_way": tw or {},
        "model": "claude-sonnet-4-5",
        "prompt_version": "P254_SEMANTIC_VISION_PROMPT_V1",
        "schema_version": "P254_SEMANTIC_INTERPRETATION_SCHEMA_V1",
        "evidence_fingerprint": "e" * 64,
        "production_write": False,
    }


def _dec(audit: Dict[str, Any], field: str) -> Dict[str, Any]:
    return evaluate_field_promotion(audit=audit, field=field)


def test_promotion_whitelist() -> None:
    rules = load_promotion_rules()
    assert is_whitelisted(semantic_type="STIRRUP", field="diameter", rules=rules) is True
    assert is_whitelisted(semantic_type="STIRRUP", field="legs", rules=rules) is True
    assert is_whitelisted(semantic_type="STIRRUP", field="spacing", rules=rules) is True
    assert is_whitelisted(semantic_type="STIRRUP", field="quantity", rules=rules) is False
    assert is_whitelisted(semantic_type="STIRRUP", field="reinforcement_role", rules=rules) is False
    assert is_whitelisted(semantic_type="LONGITUDINAL_BAR", field="diameter", rules=rules) is False
    assert is_whitelisted(semantic_type="SIDE_FACE_REINFORCEMENT", field="role", rules=rules) is False


def test_unknown_field_can_be_repaired() -> None:
    a = _audit(
        text=B46_TEXT, beam_id="B46",
        diameter=None, legs=None, spacing=[],
        vis_diameter=10, vis_legs=4, vis_spacing=[100, 150, 100],
    )
    rec = _dec(a, "diameter")
    assert rec["deterministic_status"] == "DETERMINISTIC_UNKNOWN"
    assert rec["promotion_decision"] == "CONTROLLED_RECOMPUTE"
    assert rec["production_write"] is False


def test_confirmed_field_cannot_be_overridden() -> None:
    a = _audit(
        text="3L-Y10@100C/C", beam_id="B99",
        diameter=10, legs=3, spacing=[100],
        vis_diameter=12, vis_legs=4, vis_spacing=[150],
    )
    rec = _dec(a, "diameter")
    assert rec["deterministic_status"] == "DETERMINISTIC_CONFIRMED"
    assert rec["promotion_decision"] == "BLOCKED"
    assert rec["reason"] == "CONFIRMED_FIELD_CANNOT_BE_OVERRIDDEN"


def test_partial_field_can_be_repaired() -> None:
    a = _audit(
        text=B120_TEXT, beam_id="B120",
        diameter=10, legs=3, spacing=[100],
        vis_diameter=10, vis_legs=3, vis_spacing=[100, 150, 100],
    )
    status = classify_deterministic_status(
        field="spacing", deterministic_value=[100], annotation_text=B120_TEXT,
        deterministic_type="STIRRUP",
    )
    assert status == "DETERMINISTIC_PARTIAL"
    rec = _dec(a, "spacing")
    assert rec["deterministic_status"] == "DETERMINISTIC_PARTIAL"
    assert rec["promotion_decision"] == "CONTROLLED_RECOMPUTE"


def test_b58_type_role_block() -> None:
    a = _audit(
        text=B58_TEXT, beam_id="B58",
        diameter=None, legs=None, spacing=[],
        vis_type="SIDE_FACE_REINFORCEMENT", vis_role="SIDE_FACE",
        vis_diameter=12, vis_legs=3, vis_spacing=[100],
    )
    rows = {r["field_name"]: r for r in evaluate_audit(a)}
    assert rows["semantic_type"]["promotion_decision"] != "CONTROLLED_RECOMPUTE"
    assert rows["reinforcement_role"]["promotion_decision"] != "CONTROLLED_RECOMPUTE"
    assert rows["diameter"]["promotion_decision"] == "CONTROLLED_RECOMPUTE"
    assert rows["legs"]["promotion_decision"] == "CONTROLLED_RECOMPUTE"
    assert rows["spacing"]["promotion_decision"] == "CONTROLLED_RECOMPUTE"


def test_b120_spacing_conflict() -> None:
    partial = _audit(
        text=B120_TEXT, beam_id="B120",
        diameter=10, legs=3, spacing=[100],
        vis_diameter=10, vis_legs=3, vis_spacing=[100, 150, 100],
    )
    assert _dec(partial, "spacing")["promotion_decision"] == "CONTROLLED_RECOMPUTE"
    confirmed = _audit(
        text="3L-Y10@100C/C", beam_id="B120",
        diameter=10, legs=3, spacing=[100],
        vis_diameter=10, vis_legs=3, vis_spacing=[100, 150, 100],
    )
    rec = _dec(confirmed, "spacing")
    assert rec["deterministic_status"] == "DETERMINISTIC_CONFIRMED"
    assert rec["promotion_decision"] == "BLOCKED"


def test_b46_stirrup_repair() -> None:
    a = _audit(
        text=B46_TEXT, beam_id="B46",
        diameter=None, legs=None, spacing=[],
        vis_diameter=10, vis_legs=4, vis_spacing=[100, 150, 100],
    )
    rows = {r["field_name"]: r for r in evaluate_audit(a)}
    assert rows["diameter"]["promotion_decision"] == "CONTROLLED_RECOMPUTE"
    assert rows["legs"]["promotion_decision"] == "CONTROLLED_RECOMPUTE"
    assert rows["spacing"]["promotion_decision"] == "CONTROLLED_RECOMPUTE"
    assert rows["quantity"]["promotion_decision"] != "CONTROLLED_RECOMPUTE"
    assert rows["semantic_type"]["promotion_decision"] != "CONTROLLED_RECOMPUTE"


def test_no_quantity_promotion() -> None:
    a = _audit(
        text=B46_TEXT, beam_id="B46",
        vis_diameter=10, vis_legs=4, vis_spacing=[100], vis_qty=8,
    )
    rec = _dec(a, "quantity")
    assert rec["promotion_decision"] != "CONTROLLED_RECOMPUTE"
    assert rec["reason"] in ("FORBIDDEN_FIELD", "NOT_WHITELISTED")


def test_no_zone_promotion() -> None:
    a = _audit(text=B46_TEXT, beam_id="B46", vis_diameter=10, vis_legs=4, vis_spacing=[100])
    rec = _dec(a, "zone")
    assert rec["promotion_decision"] != "CONTROLLED_RECOMPUTE"


def test_no_cut_length_promotion() -> None:
    a = _audit(text=B46_TEXT, beam_id="B46", vis_diameter=10, vis_legs=4, vis_spacing=[100])
    rec = _dec(a, "cut_length")
    assert rec["promotion_decision"] != "CONTROLLED_RECOMPUTE"
    assert rec["reason"] in ("FORBIDDEN_FIELD", "NOT_WHITELISTED")


def test_provenance_preserved() -> None:
    a = _audit(
        text=B46_TEXT, beam_id="B46",
        diameter=None, vis_diameter=10, vis_legs=4, vis_spacing=[100, 150, 100],
    )
    rec = _dec(a, "diameter")
    assert rec["object_kind"] == "VisionFieldRepairCandidate"
    assert rec["source"] == "VISION"
    assert rec["original_value"] is None
    assert rec["promoted_value"] == 10
    assert rec["evidence_fingerprint"]
    assert rec["prompt_version"]
    assert rec["candidate_id"]
    assert rec["production_write"] is False
    assert rec["promotion_class"] == "CONTROLLED_RECOMPUTE"


def test_shadow_recompute_isolated() -> None:
    original = {
        "models": [
            {
                "beam_id": "B46",
                "stirrups": [],
            }
        ]
    }
    snap = copy.deepcopy(original)
    a = _audit(
        text=B46_TEXT, beam_id="B46",
        diameter=None, legs=None, spacing=[],
        vis_diameter=10, vis_legs=4, vis_spacing=[100, 150, 100],
    )
    promoted = [r for r in evaluate_audit(a) if r["promotion_decision"] == "CONTROLLED_RECOMPUTE"]
    patched, prov = apply_repairs(r13_doc=original, audits=[a], promoted=promoted)
    assert snap == original
    assert patched["models"][0]["stirrups"]
    assert patched["models"][0]["stirrups"][0]["production_write"] is False
    assert any(p.get("action") == "INSERTED_SHADOW_STIRRUP" for p in prov)
    assert "P258-SHADOW" in patched["models"][0]["stirrups"][0]["bar_id"]


def test_production_output_unchanged() -> None:
    paths = fingerprint_paths(_v10(), {})
    before = capture_fingerprints(paths)
    a = _audit(text=B46_TEXT, beam_id="B46", vis_diameter=10, vis_legs=4, vis_spacing=[100])
    evaluate_audit(a)
    after = capture_fingerprints(paths)
    cmp = compare_fingerprints(before, after)
    assert cmp["unchanged"] is True


def test_steel_baseline_unchanged() -> None:
    paths = fingerprint_paths(_v10(), {})
    key = "fifth_r13_models"
    if key not in paths or not paths[key].exists():
        return
    before = paths[key].read_bytes()
    doc = {"models": [{"beam_id": "B1", "stirrups": [{"bar_label": "3L-Y8@100", "diameter_mm": 8}]}]}
    a = _audit(
        text="3L-Y8@100C/125/100C/C", beam_id="B1",
        diameter=8, legs=3, spacing=[100],
        vis_diameter=8, vis_legs=3, vis_spacing=[100, 125, 100],
    )
    promoted = [r for r in evaluate_audit(a) if r["promotion_decision"] == "CONTROLLED_RECOMPUTE"]
    apply_repairs(r13_doc=doc, audits=[a], promoted=promoted)
    assert paths[key].read_bytes() == before


def test_bbs_baseline_unchanged() -> None:
    paths = fingerprint_paths(_v10(), {})
    key = "fifth_bbs_summary"
    if key not in paths or not paths[key].exists():
        return
    before = paths[key].read_bytes()
    evaluate_audit(_audit(text=B46_TEXT, beam_id="B46", vis_diameter=10, vis_legs=4, vis_spacing=[100]))
    assert paths[key].read_bytes() == before


def test_excel_baseline_unchanged() -> None:
    paths = fingerprint_paths(_v10(), {})
    key = "fifth_model_excel"
    if key not in paths or not paths[key].exists():
        return
    before = paths[key].read_bytes()
    evaluate_audit(_audit(text=B46_TEXT, beam_id="B46", vis_diameter=10, vis_legs=4, vis_spacing=[100]))
    assert paths[key].read_bytes() == before


def test_p251_regression() -> None:
    p257_p251()


def test_p254_regression() -> None:
    p257_p254()


def test_p255_regression() -> None:
    p257_p255()


def test_p256_regression() -> None:
    p257_p256()


def test_p257_regression() -> None:
    fw = firewall_check(_v10())
    assert fw["ok"] is True
    paths = fingerprint_paths(_v10(), {})
    before = capture_fingerprints(paths)
    after = capture_fingerprints(paths)
    assert compare_fingerprints(before, after)["unchanged"] is True
    status = (
        _v10()
        / "data"
        / "output"
        / "PhaseP257_unseen_drawing_controlled_vision_validation"
        / "P2.5.7_STATUS.md"
    )
    assert status.exists()


def test_baseline_vs_shadow_comparison() -> None:
    est = {"beams": [{"beam_id": "B1", "steel_kg": 100.0}]}
    base = {"beams": [{"beam_id": "B1", "steel_kg": 70.0}]}
    vis = {"beams": [{"beam_id": "B1", "steel_kg": 90.0}]}
    impact = beam_improvement(estimator=est, baseline=base, shadow=vis)
    assert impact["beams_improved"] == 1
    assert impact["improved"][0]["beam_id"] == "B1"


def test_steel_accuracy_calculation() -> None:
    assert steel_accuracy_pct(36271.794, 58796.332) == 61.69
    assert steel_accuracy_pct(58796.332, 58796.332) == 100.0
    assert steel_accuracy_pct(0.0, 100.0) == 0.0


def test_beam_improvement_calculation() -> None:
    est = {
        "beams": [
            {"beam_id": "A", "steel_kg": 10.0},
            {"beam_id": "B", "steel_kg": 10.0},
            {"beam_id": "C", "steel_kg": 10.0},
        ]
    }
    base = {
        "beams": [
            {"beam_id": "A", "steel_kg": 5.0},
            {"beam_id": "B", "steel_kg": 10.0},
            {"beam_id": "C", "steel_kg": 10.0},
        ]
    }
    vis = {
        "beams": [
            {"beam_id": "A", "steel_kg": 9.0},
            {"beam_id": "B", "steel_kg": 10.0},
            {"beam_id": "C", "steel_kg": 1.0},
        ]
    }
    impact = beam_improvement(estimator=est, baseline=base, shadow=vis)
    assert impact["beams_improved"] == 1
    assert impact["beams_unchanged"] == 1
    assert impact["beams_worsened"] == 1
    assert impact["worsened"][0]["beam_id"] == "C"


def test_firewall_no_production_import() -> None:
    fw = firewall_check(_v10())
    assert fw["ok"] is True
    assert fw["offenders"] == []


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("promotion_whitelist", test_promotion_whitelist),
        ("unknown_field_can_be_repaired", test_unknown_field_can_be_repaired),
        ("confirmed_field_cannot_be_overridden", test_confirmed_field_cannot_be_overridden),
        ("partial_field_can_be_repaired", test_partial_field_can_be_repaired),
        ("B58_type_role_block", test_b58_type_role_block),
        ("B120_spacing_conflict", test_b120_spacing_conflict),
        ("B46_stirrup_repair", test_b46_stirrup_repair),
        ("no_quantity_promotion", test_no_quantity_promotion),
        ("no_zone_promotion", test_no_zone_promotion),
        ("no_cut_length_promotion", test_no_cut_length_promotion),
        ("provenance_preserved", test_provenance_preserved),
        ("shadow_recompute_isolated", test_shadow_recompute_isolated),
        ("production_output_unchanged", test_production_output_unchanged),
        ("steel_baseline_unchanged", test_steel_baseline_unchanged),
        ("BBS_baseline_unchanged", test_bbs_baseline_unchanged),
        ("Excel_baseline_unchanged", test_excel_baseline_unchanged),
        ("P2.5.1_regression", test_p251_regression),
        ("P2.5.4_regression", test_p254_regression),
        ("P2.5.5_regression", test_p255_regression),
        ("P2.5.6_regression", test_p256_regression),
        ("P2.5.7_regression", test_p257_regression),
        ("baseline_vs_shadow_comparison", test_baseline_vs_shadow_comparison),
        ("steel_accuracy_calculation", test_steel_accuracy_calculation),
        ("beam_improvement_calculation", test_beam_improvement_calculation),
    ]
    results: List[Dict[str, Any]] = []
    for name, fn in tests:
        try:
            fn()
            results.append({"name": name, "pass": True})
        except Exception as exc:  # noqa: BLE001
            results.append({"name": name, "pass": False, "error": str(exc)})
    p257 = run_p257_unit_tests()
    passed = sum(1 for r in results if r["pass"])
    return {
        "success": passed == len(tests) and bool(p257.get("success")),
        "passed": passed,
        "total": len(tests),
        "results": results,
        "p257_unit_tests": p257,
        "p256_unit_tests": p257.get("p256_unit_tests"),
        "p255_unit_tests": p257.get("p255_unit_tests"),
        "p254_unit_tests": p257.get("p254_unit_tests"),
        "model_version": MODEL_VERSION,
    }


__all__ = ["run_unit_tests"]
