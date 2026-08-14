"""Unit tests for P2.5.10. No Claude. No VB.1 in the default suite."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP259_beam_safe_arbitration.unit_tests import run_unit_tests as run_p259_unit_tests

from .beam_safety_gate import decide_insertion, filter_promoted, gate_beam
from .config import (
    CLS_CREATES_NEW,
    CLS_NO_NEW,
    CLS_SUPPLEMENT,
    DEC_ALLOW,
    DEC_HOLD,
    DEC_REJECT,
    MODEL_VERSION,
)
from .diagnostics import UNKNOWN_ONLY_IMPROVEMENT_FIXTURES, UNKNOWN_ONLY_WORSENING_FIXTURES
from .evidence_evaluator import (
    assert_runtime_context,
    build_insertion_context,
    evaluate_insertion_evidence,
)
from .insertion_classifier import classify_insertion
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def _r13(
    beam_id: str,
    *,
    stirrups: Optional[List[Dict[str, Any]]] = None,
    span: float = 4000.0,
) -> Dict[str, Any]:
    return {
        "models": [
            {
                "beam_id": beam_id,
                "geometry": {"clear_span_mm": span},
                "stirrups": list(stirrups or []),
                "top_main_bars": [{"bar_id": "T1"}],
                "bottom_main_bars": [],
                "side_face_reinforcement": [],
            }
        ]
    }


def _audit(
    *,
    text: str,
    beam_id: str,
    vis_diameter: Any = 8,
    vis_legs: Any = 2,
    vis_spacing: Any = None,
    vis_qty: Any = None,
    vis_type: str = "STIRRUP",
    vis_role: str = "STIRRUP",
    vis_assoc: str = "TARGET_BEAM",
    det_type: str = "STIRRUP",
    det_diameter: Any = None,
    det_legs: Any = None,
    det_spacing: Any = None,
    cid: str = "VC::X::ANN-1",
) -> Dict[str, Any]:
    return {
        "candidate_id": cid.replace("X", beam_id),
        "beam_id": beam_id,
        "annotation_id": "ANN-1",
        "annotation_text": text,
        "invoke_claude": True,
        "shadow_trigger_reason": ["OCR_UNCERTAIN"] if "\\X" in text else ["DIAMETER_UNCERTAIN"],
        "deterministic_result": {
            "semantic_type": det_type,
            "reinforcement_role": "STIRRUP",
            "diameter_value_mm": det_diameter,
            "leg_count": det_legs,
            "spacing_values_mm": list(det_spacing or []),
            "quantity_value": None,
        },
        "vision_result": {
            "semantic_type": vis_type,
            "role": vis_role,
            "diameter_mm": vis_diameter,
            "legs": vis_legs,
            "spacing_mm": list(vis_spacing or [100]),
            "quantity": vis_qty,
            "beam_association": vis_assoc,
        },
    }


def _promoted(audit: Dict[str, Any], field: str, value: Any) -> Dict[str, Any]:
    return {
        "candidate_id": audit["candidate_id"],
        "beam_id": audit["beam_id"],
        "annotation_text": audit["annotation_text"],
        "field_name": field,
        "promotion_decision": "CONTROLLED_RECOMPUTE",
        "promoted_value": value,
        "deterministic_status": "DETERMINISTIC_UNKNOWN",
        "production_write": False,
    }


def _bundle(audit: Dict[str, Any], *, dia: Any = 8, legs: Any = 2, spacing: Any = None) -> List[Dict[str, Any]]:
    return [
        _promoted(audit, "diameter", dia),
        _promoted(audit, "legs", legs),
        _promoted(audit, "spacing", list(spacing or [100])),
    ]


def _ctx(r13: Dict[str, Any], audit: Dict[str, Any], peers: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    beam = r13["models"][0]
    return build_insertion_context(beam=beam, audit=audit, peer_audits=peers or [audit], owned_by_beam=True)


def test_no_new_stirrup() -> None:
    beam_id = "BX"
    r13 = _r13(
        beam_id,
        stirrups=[
            {
                "bar_id": "S1",
                "diameter_mm": 8.0,
                "spacing_mm": 100.0,
                "spacing_pattern": "100",
                "bar_label": "2L-Y8@100",
                "semantic_role": "STIRRUP",
            }
        ],
    )
    audit = _audit(text="2L-Y8@100C/C", beam_id=beam_id, vis_spacing=[100])
    cls = classify_insertion(r13_doc=r13, audits=[audit], promoted=_bundle(audit), beam_id=beam_id, span_mm=4000)
    assert cls["classification"] == CLS_NO_NEW
    assert cls["new_stirrup_object"] is False
    assert cls["existing_stirrup_match"] is True


def test_supplements_existing_stirrup() -> None:
    beam_id = "BX"
    r13 = _r13(
        beam_id,
        stirrups=[
            {
                "bar_id": "S1",
                "diameter_mm": 8.0,
                "spacing_mm": None,
                "spacing_pattern": "",
                "bar_label": "2L-Y8@",
                "semantic_role": "STIRRUP",
            }
        ],
    )
    audit = _audit(text="2L-Y8@100C/C", beam_id=beam_id, vis_spacing=[100])
    cls = classify_insertion(r13_doc=r13, audits=[audit], promoted=_bundle(audit), beam_id=beam_id, span_mm=4000)
    assert cls["classification"] == CLS_SUPPLEMENT
    assert cls["new_stirrup_object"] is False
    assert cls["existing_stirrup_match"] is True


def test_creates_new_stirrup() -> None:
    beam_id = "BX"
    r13 = _r13(beam_id, stirrups=[])
    audit = _audit(text="2L-Y8@\\X100C/C", beam_id=beam_id, vis_spacing=[100])
    cls = classify_insertion(r13_doc=r13, audits=[audit], promoted=_bundle(audit), beam_id=beam_id, span_mm=4000)
    assert cls["classification"] == CLS_CREATES_NEW
    assert cls["new_stirrup_object"] is True
    assert cls["existing_stirrup_match"] is False


def test_existing_stirrup_match() -> None:
    test_supplements_existing_stirrup()
    test_no_new_stirrup()


def test_new_zone_detection() -> None:
    beam_id = "BX"
    r13 = _r13(beam_id, stirrups=[])
    audit = _audit(text="2L-Y8@\\X100/150/100C/C", beam_id=beam_id, vis_spacing=[100, 150, 100])
    cls = classify_insertion(
        r13_doc=r13, audits=[audit], promoted=_bundle(audit, spacing=[100, 150, 100]), beam_id=beam_id, span_mm=4000
    )
    assert cls["new_zone"] is True


def test_new_piece_detection() -> None:
    beam_id = "BX"
    r13 = _r13(beam_id, stirrups=[])
    audit = _audit(text="2L-Y8@\\X100C/C", beam_id=beam_id)
    cls = classify_insertion(r13_doc=r13, audits=[audit], promoted=_bundle(audit), beam_id=beam_id, span_mm=4000)
    assert cls["new_piece"] is True


def test_new_steel_detection() -> None:
    beam_id = "BX"
    r13 = _r13(beam_id, stirrups=[])
    audit = _audit(text="2L-Y8@\\X100C/C", beam_id=beam_id)
    cls = classify_insertion(r13_doc=r13, audits=[audit], promoted=_bundle(audit), beam_id=beam_id, span_mm=4000)
    assert cls["new_steel"] is True


def test_deterministic_semantic_conflict() -> None:
    beam_id = "BX"
    r13 = _r13(beam_id, stirrups=[])
    audit = _audit(
        text="2L-Y8@\\X100C/C",
        beam_id=beam_id,
        vis_type="SIDE_FACE_REINFORCEMENT",
        vis_role="SIDE_FACE",
    )
    ctx = _ctx(r13, audit)
    cls = classify_insertion(r13_doc=r13, audits=[audit], promoted=_bundle(audit), beam_id=beam_id, span_mm=4000)
    ev = evaluate_insertion_evidence(ctx=ctx, classification=cls, promoted=_bundle(audit))
    gate = decide_insertion(classification=cls, evidence=ev)
    assert gate["decision"] == DEC_REJECT
    assert any("SEMANTIC" in c for c in gate["reason_codes"])


def test_unsupported_new_stirrup() -> None:
    beam_id = "BX"
    r13 = _r13(beam_id, stirrups=[])
    audit = _audit(text="2L-Y8@\\X100C/C", beam_id=beam_id)
    ctx = _ctx(r13, audit)
    result = gate_beam(r13_doc=r13, audits=[audit], promoted=_bundle(audit), beam_id=beam_id, ctx=ctx)
    assert result["classification"] == CLS_CREATES_NEW
    assert result["decision"] == DEC_HOLD
    assert any("INSUFFICIENT" in c or "UNSUPPORTED_NEW_STIRRUP" in c for c in result["reason_codes"])


def test_sufficient_production_evidence() -> None:
    beam_id = "BX"
    r13 = _r13(beam_id, stirrups=[])
    audit = _audit(text="2L-Y8@\\X100/150/100C/C", beam_id=beam_id, vis_spacing=[100, 150, 100])
    ctx = _ctx(r13, audit)
    result = gate_beam(
        r13_doc=r13,
        audits=[audit],
        promoted=_bundle(audit, spacing=[100, 150, 100]),
        beam_id=beam_id,
        ctx=ctx,
    )
    assert result["classification"] == CLS_CREATES_NEW
    assert result["decision"] == DEC_ALLOW
    assert ctx["complete_schedule_in_text"] is True


def test_insufficient_production_evidence() -> None:
    test_unsupported_new_stirrup()


def test_invalid_diameter() -> None:
    beam_id = "BX"
    r13 = _r13(beam_id, stirrups=[])
    audit = _audit(text="2L-Y99@\\X100C/C", beam_id=beam_id, vis_diameter=99)
    ctx = _ctx(r13, audit)
    result = gate_beam(
        r13_doc=r13, audits=[audit], promoted=_bundle(audit, dia=99), beam_id=beam_id, ctx=ctx
    )
    assert result["decision"] == DEC_REJECT
    assert any("DIAMETER" in c for c in result["reason_codes"])


def test_invalid_spacing() -> None:
    beam_id = "BX"
    r13 = _r13(beam_id, stirrups=[])
    audit = _audit(text="2L-Y8@\\X5C/C", beam_id=beam_id, vis_spacing=[5])
    ctx = _ctx(r13, audit)
    result = gate_beam(
        r13_doc=r13, audits=[audit], promoted=_bundle(audit, spacing=[5]), beam_id=beam_id, ctx=ctx
    )
    assert result["decision"] == DEC_REJECT
    assert any("SPACING" in c for c in result["reason_codes"])


def test_invalid_legs() -> None:
    beam_id = "BX"
    r13 = _r13(beam_id, stirrups=[])
    audit = _audit(text="99L-Y8@\\X100C/C", beam_id=beam_id, vis_legs=99)
    ctx = _ctx(r13, audit)
    result = gate_beam(
        r13_doc=r13, audits=[audit], promoted=_bundle(audit, legs=99), beam_id=beam_id, ctx=ctx
    )
    assert result["decision"] == DEC_REJECT
    assert any("LEGS" in c for c in result["reason_codes"])


def test_invented_quantity_rejection() -> None:
    beam_id = "BX"
    r13 = _r13(beam_id, stirrups=[])
    audit = _audit(text="2L-Y8@\\X100C/C", beam_id=beam_id, vis_qty=12)
    promoted = _bundle(audit) + [_promoted(audit, "quantity", 12)]
    ctx = _ctx(r13, audit)
    result = gate_beam(r13_doc=r13, audits=[audit], promoted=promoted, beam_id=beam_id, ctx=ctx)
    assert result["decision"] == DEC_REJECT
    assert any("QUANTITY" in c for c in result["reason_codes"])


def test_beam_association_conflict() -> None:
    beam_id = "BX"
    r13 = _r13(beam_id, stirrups=[])
    audit = _audit(text="2L-Y8@\\X100C/C", beam_id=beam_id, vis_assoc="OTHER_BEAM")
    ctx = _ctx(r13, audit)
    result = gate_beam(r13_doc=r13, audits=[audit], promoted=_bundle(audit), beam_id=beam_id, ctx=ctx)
    assert result["decision"] == DEC_REJECT
    assert any("ASSOCIATION" in c for c in result["reason_codes"])


def test_no_production_mutation() -> None:
    paths = fingerprint_paths(_v10(), {})
    before = capture_fingerprints(paths)
    beam_id = "BX"
    r13 = _r13(beam_id, stirrups=[])
    original = json.dumps(r13, sort_keys=True)
    audit = _audit(text="2L-Y8@\\X100C/C", beam_id=beam_id)
    ctx = _ctx(r13, audit)
    filter_promoted(r13_doc=r13, audits=[audit], promoted=_bundle(audit), contexts={beam_id: ctx})
    assert json.dumps(r13, sort_keys=True) == original
    after = capture_fingerprints(paths)
    assert compare_fingerprints(before, after)["unchanged"] is True
    fw = firewall_check(_v10())
    assert fw["ok"] is True


def test_no_steel_mutation() -> None:
    paths = fingerprint_paths(_v10(), {})
    before = capture_fingerprints({"fifth_model_excel": paths["fifth_model_excel"]})
    test_no_production_mutation()
    after = capture_fingerprints({"fifth_model_excel": paths["fifth_model_excel"]})
    assert compare_fingerprints(before, after)["unchanged"] is True


def test_no_bbs_mutation() -> None:
    paths = fingerprint_paths(_v10(), {})
    before = capture_fingerprints({"fifth_bbs_summary": paths["fifth_bbs_summary"]})
    test_creates_new_stirrup()
    after = capture_fingerprints({"fifth_bbs_summary": paths["fifth_bbs_summary"]})
    assert compare_fingerprints(before, after)["unchanged"] is True


def test_no_excel_mutation() -> None:
    test_no_steel_mutation()


def test_estimator_leakage_rejection() -> None:
    try:
        assert_runtime_context({"span_mm": 4000, "estimator_kg": 1.0})
        raise AssertionError("evaluation-only context key must raise")
    except ValueError as exc:
        assert "unsupported runtime context key" in str(exc)


def test_benchmark_answer_leakage_rejection() -> None:
    try:
        assert_runtime_context({"benchmark_answer": 99})
        raise AssertionError("evaluation-only context key must raise")
    except ValueError as exc:
        assert "unsupported runtime context key" in str(exc)
    scan = runtime_leakage_scan(_pkg())
    assert scan["ok"] is True, scan


def test_p259_regression() -> None:
    nested = run_p259_unit_tests()
    assert nested.get("success") is True


def test_p258_regression() -> None:
    from PhaseP258_controlled_vision_field_repair.unit_tests import run_unit_tests as run_p258

    nested = run_p258()
    assert nested.get("success") is True


def test_current_worsening_case_diagnostics() -> None:
    assert len(UNKNOWN_ONLY_WORSENING_FIXTURES) == 10
    beam_id = "BX"
    r13 = _r13(beam_id, stirrups=[])
    audit = _audit(text="4L-Y12@\\X100C/C", beam_id=beam_id, vis_diameter=12, vis_legs=4, vis_spacing=[100])
    ctx = _ctx(r13, audit)
    result = gate_beam(
        r13_doc=r13,
        audits=[audit],
        promoted=_bundle(audit, dia=12, legs=4, spacing=[100]),
        beam_id=beam_id,
        ctx=ctx,
    )
    assert result["classification"] == CLS_CREATES_NEW
    assert result["decision"] == DEC_HOLD
    assert result["insertion"]["new_stirrup_object"] is True


def test_current_improvement_case_preservation() -> None:
    assert "B128" in UNKNOWN_ONLY_IMPROVEMENT_FIXTURES
    beam_id = "BX"
    r13 = _r13(beam_id, stirrups=[])
    audit = _audit(text="2L-Y8@\\X100/150/100C/C", beam_id=beam_id, vis_spacing=[100, 150, 100])
    ctx = _ctx(r13, audit)
    result = gate_beam(
        r13_doc=r13,
        audits=[audit],
        promoted=_bundle(audit, spacing=[100, 150, 100]),
        beam_id=beam_id,
        ctx=ctx,
    )
    assert result["decision"] == DEC_ALLOW


def test_model_detected_universe_143() -> None:
    locator_root = (
        _v10()
        / "data"
        / "web_runs"
        / "qa2_Fifth_Set_Drawings_20260806_142822"
        / "data"
        / "output"
        / "PhaseR1.3_pipeline_integration"
        / "beam_reinforcement_models_production.json"
    )
    assert locator_root.exists()
    doc = json.loads(locator_root.read_text(encoding="utf-8"))
    ids = {m.get("beam_id") for m in (doc.get("models") or []) if isinstance(m, dict)}
    assert len(ids) == 143


def test_deterministic_fingerprint_unchanged() -> None:
    paths = fingerprint_paths(_v10(), {})
    before = capture_fingerprints(
        {
            "fifth_r13_models": paths["fifth_r13_models"],
            "p259_status": paths["p259_status"],
        }
    )
    test_no_production_mutation()
    after = capture_fingerprints(
        {
            "fifth_r13_models": paths["fifth_r13_models"],
            "p259_status": paths["p259_status"],
        }
    )
    assert compare_fingerprints(before, after)["unchanged"] is True
    assert MODEL_VERSION == "10.9.0"


def test_supplement_is_allowed() -> None:
    beam_id = "BX"
    r13 = _r13(
        beam_id,
        stirrups=[
            {
                "bar_id": "S1",
                "diameter_mm": 8.0,
                "spacing_mm": None,
                "bar_label": "2L-Y8@",
                "semantic_role": "STIRRUP",
            }
        ],
    )
    audit = _audit(text="2L-Y8@100C/C", beam_id=beam_id)
    ctx = _ctx(r13, audit)
    result = gate_beam(r13_doc=r13, audits=[audit], promoted=_bundle(audit), beam_id=beam_id, ctx=ctx)
    assert result["classification"] == CLS_SUPPLEMENT
    assert result["decision"] == DEC_ALLOW


def test_no_new_is_allowed() -> None:
    beam_id = "BX"
    r13 = _r13(
        beam_id,
        stirrups=[
            {
                "bar_id": "S1",
                "diameter_mm": 8.0,
                "spacing_mm": 100.0,
                "spacing_pattern": "100",
                "bar_label": "2L-Y8@100",
                "semantic_role": "STIRRUP",
            }
        ],
    )
    audit = _audit(text="2L-Y8@100C/C", beam_id=beam_id)
    ctx = _ctx(r13, audit)
    result = gate_beam(r13_doc=r13, audits=[audit], promoted=_bundle(audit), beam_id=beam_id, ctx=ctx)
    assert result["classification"] == CLS_NO_NEW
    assert result["decision"] == DEC_ALLOW


def test_second_stirrup_family_rejected() -> None:
    beam_id = "BX"
    r13 = _r13(
        beam_id,
        stirrups=[
            {"bar_id": "S1", "diameter_mm": 8.0, "spacing_pattern": "100", "semantic_role": "STIRRUP"},
            {"bar_id": "S2", "diameter_mm": 10.0, "spacing_pattern": "150", "semantic_role": "STIRRUP"},
        ],
    )
    audit = _audit(text="2L-Y12@100C/C", beam_id=beam_id, vis_diameter=12)
    ctx = _ctx(r13, audit)
    result = gate_beam(
        r13_doc=r13, audits=[audit], promoted=_bundle(audit, dia=12), beam_id=beam_id, ctx=ctx
    )
    assert result["classification"] == CLS_CREATES_NEW
    assert result["decision"] == DEC_REJECT
    assert any("INCOMPATIBLE" in c for c in result["reason_codes"])


def test_caller_r13_not_mutated() -> None:
    beam_id = "BX"
    r13 = _r13(beam_id, stirrups=[])
    snapshot = copy.deepcopy(r13)
    audit = _audit(text="2L-Y8@\\X100C/C", beam_id=beam_id)
    classify_insertion(r13_doc=r13, audits=[audit], promoted=_bundle(audit), beam_id=beam_id, span_mm=4000)
    assert r13 == snapshot


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("no_new_stirrup", test_no_new_stirrup),
        ("supplements_existing_stirrup", test_supplements_existing_stirrup),
        ("creates_new_stirrup", test_creates_new_stirrup),
        ("existing_stirrup_match", test_existing_stirrup_match),
        ("new_zone_detection", test_new_zone_detection),
        ("new_piece_detection", test_new_piece_detection),
        ("new_steel_detection", test_new_steel_detection),
        ("deterministic_semantic_conflict", test_deterministic_semantic_conflict),
        ("unsupported_new_stirrup", test_unsupported_new_stirrup),
        ("sufficient_production_evidence", test_sufficient_production_evidence),
        ("insufficient_production_evidence", test_insufficient_production_evidence),
        ("invalid_diameter", test_invalid_diameter),
        ("invalid_spacing", test_invalid_spacing),
        ("invalid_legs", test_invalid_legs),
        ("invented_quantity_rejection", test_invented_quantity_rejection),
        ("beam_association_conflict", test_beam_association_conflict),
        ("no_production_mutation", test_no_production_mutation),
        ("no_steel_mutation", test_no_steel_mutation),
        ("no_bbs_mutation", test_no_bbs_mutation),
        ("no_excel_mutation", test_no_excel_mutation),
        ("estimator_leakage_rejection", test_estimator_leakage_rejection),
        ("benchmark_answer_leakage_rejection", test_benchmark_answer_leakage_rejection),
        ("P2.5.9_regression", test_p259_regression),
        ("P2.5.8_regression", test_p258_regression),
        ("current_worsening_case_diagnostics", test_current_worsening_case_diagnostics),
        ("current_improvement_case_preservation", test_current_improvement_case_preservation),
        ("model_detected_universe_143", test_model_detected_universe_143),
        ("deterministic_fingerprint_unchanged", test_deterministic_fingerprint_unchanged),
        ("supplement_is_allowed", test_supplement_is_allowed),
        ("no_new_is_allowed", test_no_new_is_allowed),
        ("second_stirrup_family_rejected", test_second_stirrup_family_rejected),
        ("caller_r13_not_mutated", test_caller_r13_not_mutated),
    ]
    results: List[Dict[str, Any]] = []
    for name, fn in tests:
        try:
            fn()
            results.append({"name": name, "pass": True})
        except Exception as exc:  # noqa: BLE001
            results.append({"name": name, "pass": False, "error": str(exc)})
    passed = sum(1 for r in results if r["pass"])
    p259 = next((r for r in results if r["name"] == "P2.5.9_regression"), {})
    return {
        "success": passed == len(tests),
        "passed": passed,
        "total": len(tests),
        "results": results,
        "p259_nested_ok": bool(p259.get("pass")),
        "model_version": MODEL_VERSION,
    }


__all__ = ["run_unit_tests"]
