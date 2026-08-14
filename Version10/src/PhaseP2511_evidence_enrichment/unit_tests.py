"""Unit tests for P2.5.11. No Claude. No VB.1 in the default suite."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from PhaseP2510_new_stirrup_safety.beam_safety_gate import gate_beam as p2510_gate
from PhaseP2510_new_stirrup_safety.evidence_evaluator import build_insertion_context
from PhaseP2510_new_stirrup_safety.unit_tests import run_unit_tests as run_p2510_unit_tests

from .config import DEC_ALLOW, DEC_HOLD, DEC_REJECT, MODEL_VERSION
from .diagnostics import P2510_ALLOW_FIXTURES, UNKNOWN_ONLY_WORSENING_FIXTURES
from .enrichment_gate import enrich_decision
from .evidence_resolver import assert_runtime_context, build_enrichment_context
from .notation_quality import classify_annotation_quality
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


def _r13(beam_id: str, *, stirrups=None, span: float = 4000.0, bottom: bool = False) -> Dict[str, Any]:
    return {
        "models": [
            {
                "beam_id": beam_id,
                "geometry": {"clear_span_mm": span},
                "stirrups": list(stirrups or []),
                "top_main_bars": [{"bar_id": "T1"}],
                "bottom_main_bars": ([{"bar_id": "B1"}] if bottom else []),
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
    vis_assoc: str = "TARGET_BEAM",
    vis_type: str = "STIRRUP",
    vis_role: str = "STIRRUP",
    vis_qty: Any = None,
    det_type: str = "STIRRUP",
) -> Dict[str, Any]:
    return {
        "candidate_id": f"VC::{beam_id}::ANN-1",
        "beam_id": beam_id,
        "annotation_id": "ANN-1",
        "annotation_text": text,
        "invoke_claude": True,
        "shadow_trigger_reason": ["OCR_UNCERTAIN"] if "\\X" in text else ["DIAMETER_UNCERTAIN"],
        "deterministic_result": {
            "semantic_type": det_type,
            "reinforcement_role": "STIRRUP",
            "diameter_value_mm": None,
            "leg_count": None,
            "spacing_values_mm": [],
            "quantity_value": None,
            "evidence_links": {"leader_id": "LDR::1", "chain_semantic_type": "StirrupNote"},
        },
        "vision_result": {
            "semantic_type": vis_type,
            "role": vis_role,
            "diameter_mm": vis_diameter,
            "legs": vis_legs,
            "spacing_mm": list(vis_spacing or [100]),
            "quantity": vis_qty,
            "beam_association": vis_assoc,
            "normalized_notation": text.replace("\\X", ""),
        },
    }


def _promoted(audit: Dict[str, Any], *, dia=8, legs=2, spacing=None) -> List[Dict[str, Any]]:
    sp = list(spacing or [100])
    out = []
    for field, value in (("diameter", dia), ("legs", legs), ("spacing", sp)):
        out.append(
            {
                "candidate_id": audit["candidate_id"],
                "beam_id": audit["beam_id"],
                "annotation_text": audit["annotation_text"],
                "field_name": field,
                "promotion_decision": "CONTROLLED_RECOMPUTE",
                "promoted_value": value,
                "deterministic_status": "DETERMINISTIC_UNKNOWN",
                "production_write": False,
            }
        )
    return out


def _run(text: str, **kwargs) -> Dict[str, Any]:
    beam_id = kwargs.pop("beam_id", "BX")
    span = kwargs.pop("span", 4000.0)
    stirrups = kwargs.pop("stirrups", [])
    r13 = _r13(beam_id, stirrups=stirrups, span=span, bottom=kwargs.pop("bottom", True))
    audit = _audit(text=text, beam_id=beam_id, **kwargs)
    promoted = _promoted(
        audit,
        dia=audit["vision_result"]["diameter_mm"],
        legs=audit["vision_result"]["legs"],
        spacing=audit["vision_result"]["spacing_mm"],
    )
    p2510_ctx = build_insertion_context(beam=r13["models"][0], audit=audit, owned_by_beam=True)
    p2511_ctx = build_enrichment_context(beam=r13["models"][0], audit=audit, owned_by_beam=True)
    p2510 = p2510_gate(r13_doc=r13, audits=[audit], promoted=promoted, beam_id=beam_id, ctx=p2510_ctx)
    return enrich_decision(p2510_result=p2510, ctx=p2511_ctx)


def test_valid_uniform_with_association_allow() -> None:
    r = _run("2L-Y8@100")
    assert r["p2510_decision"] == DEC_HOLD
    assert r["decision"] == DEC_ALLOW
    assert r["evidence_strength"] == "STRONG"


def test_valid_uniform_unknown_deterministic_allow() -> None:
    r = _run("3L-Y10@100", vis_diameter=10, vis_legs=3)
    assert r["decision"] == DEC_ALLOW


def test_valid_schedule_allow() -> None:
    r = _run("2L-Y8@\\X100/150/100C/C", vis_spacing=[100, 150, 100])
    assert r["decision"] == DEC_ALLOW


def test_valid_notation_plus_plausibility_allow() -> None:
    r = _run("4L-Y10@100", vis_diameter=10, vis_legs=4, bottom=True)
    assert r["decision"] == DEC_ALLOW
    assert True in [True] and r["resolved"]["engineering_plausibility"] is True


def test_malformed_ocr_hold() -> None:
    r = _run("@\\X100C/C", vis_diameter=8, vis_legs=2)
    assert r["decision"] in (DEC_HOLD, DEC_REJECT)


def test_truncated_spacing_hold() -> None:
    r = _run("2L-Y8@\\X100C/C")
    assert r["decision"] == DEC_HOLD
    assert any("OCR" in c or "TRUNCATED" in c for c in r["reason_codes"])


def test_invalid_diameter() -> None:
    r = _run("2L-Y99@100", vis_diameter=99)
    assert r["decision"] in (DEC_HOLD, DEC_REJECT)


def test_invalid_legs() -> None:
    r = _run("99L-Y8@100", vis_legs=99)
    assert r["decision"] in (DEC_HOLD, DEC_REJECT)


def test_invalid_spacing() -> None:
    r = _run("2L-Y8@5", vis_spacing=[5])
    assert r["decision"] in (DEC_HOLD, DEC_REJECT)


def test_unresolved_association_hold() -> None:
    r = _run("2L-Y8@100", vis_assoc="UNCERTAIN")
    assert r["decision"] == DEC_HOLD


def test_conflicting_association() -> None:
    r = _run("2L-Y8@100", vis_assoc="OTHER_BEAM")
    assert r["decision"] in (DEC_HOLD, DEC_REJECT)


def test_plausibility_without_notation_hold() -> None:
    r = _run("BEAM NOTE ONLY", vis_diameter=8, vis_legs=2, vis_spacing=[100])
    assert r["decision"] == DEC_HOLD


def test_no_invention_from_beam_existence() -> None:
    r = _run("", vis_diameter=None, vis_legs=None, vis_spacing=[])
    assert not (r.get("classification") == "CREATES_NEW_STIRRUP" and r["decision"] == DEC_ALLOW)


def test_existing_stirrup_unchanged() -> None:
    stirrups = [
        {
            "bar_id": "S1",
            "diameter_mm": 8.0,
            "spacing_mm": 100.0,
            "spacing_pattern": "100",
            "bar_label": "2L-Y8@100",
            "semantic_role": "STIRRUP",
        }
    ]
    r = _run("2L-Y8@100", stirrups=stirrups)
    assert r["classification"] in ("NO_NEW_STIRRUP", "SUPPLEMENTS_EXISTING_STIRRUP")
    assert r["decision"] == DEC_ALLOW


def test_supplement_remains_safe() -> None:
    stirrups = [
        {
            "bar_id": "S1",
            "diameter_mm": 8.0,
            "spacing_mm": None,
            "bar_label": "2L-Y8@",
            "semantic_role": "STIRRUP",
        }
    ]
    r = _run("2L-Y8@100", stirrups=stirrups)
    assert r["classification"] == "SUPPLEMENTS_EXISTING_STIRRUP"
    assert r["decision"] == DEC_ALLOW


def test_p2510_regression() -> None:
    nested = run_p2510_unit_tests()
    assert nested.get("success") is True


def test_p259_regression() -> None:
    from PhaseP259_beam_safe_arbitration.unit_tests import run_unit_tests as run_p259

    nested = run_p259()
    assert nested.get("success") is True


def test_no_production_mutation() -> None:
    paths = fingerprint_paths(_v10(), {})
    before = capture_fingerprints(paths)
    _run("2L-Y8@100")
    after = capture_fingerprints(paths)
    assert compare_fingerprints(before, after)["unchanged"] is True
    assert firewall_check(_v10())["ok"] is True


def test_no_steel_bbs_excel_mutation() -> None:
    paths = fingerprint_paths(_v10(), {})
    keys = ["fifth_model_excel", "fifth_bbs_summary", "fifth_r13_models"]
    before = capture_fingerprints({k: paths[k] for k in keys if k in paths})
    _run("4L-Y12@\\X100C/C", vis_diameter=12, vis_legs=4)
    after = capture_fingerprints({k: paths[k] for k in keys if k in paths})
    assert compare_fingerprints(before, after)["unchanged"] is True


def test_estimator_leakage_rejection() -> None:
    try:
        assert_runtime_context({"span_mm": 1, "estimator_kg": 1})
        raise AssertionError("must raise")
    except ValueError as exc:
        assert "unsupported runtime context key" in str(exc)


def test_benchmark_leakage_rejection() -> None:
    try:
        assert_runtime_context({"benchmark_answer": 1})
        raise AssertionError("must raise")
    except ValueError as exc:
        assert "unsupported runtime context key" in str(exc)
    assert runtime_leakage_scan(_pkg())["ok"] is True


def test_known_worsening_pattern_blocked() -> None:
    assert len(UNKNOWN_ONLY_WORSENING_FIXTURES) == 10
    r = _run("4L-Y12@\\X100C/C", vis_diameter=12, vis_legs=4)
    assert r["decision"] == DEC_HOLD
    r2 = _run("5L-Y12@\\X100C/C", vis_diameter=12, vis_legs=5)
    assert r2["decision"] == DEC_HOLD


def test_p2510_allow_fixtures_remain_allow() -> None:
    assert "B128" in P2510_ALLOW_FIXTURES
    r = _run("2L-Y8@\\X100/150/100C/C", vis_spacing=[100, 150, 100])
    assert r["decision"] == DEC_ALLOW
    r2 = _run("4L-Y10@\\X100/125/100C/C", vis_diameter=10, vis_legs=4, vis_spacing=[100, 125, 100])
    assert r2["decision"] == DEC_ALLOW


def test_held_recovery_promoted_when_valid() -> None:
    r = _run("2L-Y8@100")
    assert classify_annotation_quality("2L-Y8@100") == "CLEAN_COMPLETE"
    assert r["p2510_decision"] == DEC_HOLD
    assert r["decision"] == DEC_ALLOW


def test_model_version() -> None:
    assert MODEL_VERSION == "10.10.0"


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("valid_uniform_with_association_allow", test_valid_uniform_with_association_allow),
        ("valid_uniform_unknown_deterministic_allow", test_valid_uniform_unknown_deterministic_allow),
        ("valid_schedule_allow", test_valid_schedule_allow),
        ("valid_notation_plus_plausibility_allow", test_valid_notation_plus_plausibility_allow),
        ("malformed_ocr_hold", test_malformed_ocr_hold),
        ("truncated_spacing_hold", test_truncated_spacing_hold),
        ("invalid_diameter", test_invalid_diameter),
        ("invalid_legs", test_invalid_legs),
        ("invalid_spacing", test_invalid_spacing),
        ("unresolved_association_hold", test_unresolved_association_hold),
        ("conflicting_association", test_conflicting_association),
        ("plausibility_without_notation_hold", test_plausibility_without_notation_hold),
        ("no_invention_from_beam_existence", test_no_invention_from_beam_existence),
        ("existing_stirrup_unchanged", test_existing_stirrup_unchanged),
        ("supplement_remains_safe", test_supplement_remains_safe),
        ("P2.5.10_regression", test_p2510_regression),
        ("P2.5.9_regression", test_p259_regression),
        ("no_production_mutation", test_no_production_mutation),
        ("no_steel_bbs_excel_mutation", test_no_steel_bbs_excel_mutation),
        ("estimator_leakage_rejection", test_estimator_leakage_rejection),
        ("benchmark_leakage_rejection", test_benchmark_leakage_rejection),
        ("known_worsening_pattern_blocked", test_known_worsening_pattern_blocked),
        ("p2510_allow_fixtures_remain_allow", test_p2510_allow_fixtures_remain_allow),
        ("held_recovery_promoted_when_valid", test_held_recovery_promoted_when_valid),
        ("model_version", test_model_version),
    ]
    results: List[Dict[str, Any]] = []
    for name, fn in tests:
        try:
            fn()
            results.append({"name": name, "pass": True})
        except Exception as exc:  # noqa: BLE001
            results.append({"name": name, "pass": False, "error": str(exc)})
    passed = sum(1 for r in results if r["pass"])
    return {
        "success": passed == len(tests),
        "passed": passed,
        "total": len(tests),
        "results": results,
        "model_version": MODEL_VERSION,
    }


__all__ = ["run_unit_tests"]
