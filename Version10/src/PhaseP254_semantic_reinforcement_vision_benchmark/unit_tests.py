"""Unit tests for P2.5.4 (no live Claude calls)."""
from __future__ import annotations

from typing import Any, Dict, List

from .benchmark_builder import derive_ground_truth
from .benchmark_evaluator import evaluate_against_ground_truth
from .config import EVAL_EXACT, EVAL_HALLUCINATION, STATUS_RESOLVED
from .semantic_schema import extract_json_object, normalize_parsed
from .shadow_resolver import assert_shadow_not_production, build_shadow_result
from .validator import validate_interpretation
from .vision_prompt import SYSTEM_PROMPT, assert_no_truth_leak, build_user_prompt

MODEL_VERSION = "10.8.0"


def test_longitudinal_oracle() -> None:
    gt = derive_ground_truth(
        {
            "raw_text": "4-Y25",
            "semantic_type": "LONGITUDINAL_BAR",
            "reinforcement_role": "TOP_BAR",
            "quantity_status": "EXPLICIT",
            "quantity_value": 4,
            "diameter_value_mm": 25.0,
        }
    )
    assert gt["available"]
    assert gt["semantic_type"] == "LONGITUDINAL_BAR"
    assert gt["quantity"] == 4
    assert gt["diameter_mm"] == 25.0
    assert gt["role"] == "TOP_BAR"


def test_sfr_oracle_no_invented_quantity() -> None:
    gt = derive_ground_truth(
        {
            "raw_text": "S.F.R.ON EACH FACE",
            "semantic_type": "UNKNOWN",
            "reinforcement_role": "UNKNOWN",
            "quantity_status": "UNRESOLVED",
        }
    )
    assert gt["semantic_type"] == "SIDE_FACE_REINFORCEMENT"
    assert gt["role"] == "SIDE_FACE"
    assert gt["quantity"] is None
    assert gt["diameter_mm"] is None


def test_stirrup_rejects_quantity() -> None:
    parsed = normalize_parsed(
        {
            "candidate_id": "VC::B100::ANN-x",
            "interpretation_status": STATUS_RESOLVED,
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
    v = validate_interpretation(parsed=parsed, expected_candidate_id="VC::B100::ANN-x")
    assert v["valid"] is False
    assert "STIRRUP_MUST_NOT_HAVE_LONGITUDINAL_QUANTITY" in v["errors"]


def test_validator_accepts_longitudinal() -> None:
    parsed = normalize_parsed(
        {
            "candidate_id": "VC::B97A::ANN-d7128f62",
            "interpretation_status": STATUS_RESOLVED,
            "semantic_type": "LONGITUDINAL_BAR",
            "role": "TOP_BAR",
            "quantity": 4,
            "diameter_mm": 25,
            "legs": None,
            "spacing_mm": [],
            "beam_association": "TARGET_BEAM",
            "zone": "SUPPORT",
            "confidence": 0.9,
        }
    )
    v = validate_interpretation(
        parsed=parsed, expected_candidate_id="VC::B97A::ANN-d7128f62"
    )
    assert v["valid"] is True


def test_exact_longitudinal_eval() -> None:
    gt = derive_ground_truth(
        {
            "raw_text": "4-Y25",
            "semantic_type": "LONGITUDINAL_BAR",
            "reinforcement_role": "TOP_BAR",
            "quantity_status": "EXPLICIT",
            "quantity_value": 4,
            "diameter_value_mm": 25.0,
        }
    )
    parsed = normalize_parsed(
        {
            "candidate_id": "VC::B97A::ANN-d7128f62",
            "interpretation_status": STATUS_RESOLVED,
            "semantic_type": "LONGITUDINAL_BAR",
            "role": "SUPPORT_TOP",
            "quantity": 4,
            "diameter_mm": 25,
            "beam_association": "TARGET_BEAM",
            "zone": "SUPPORT",
            "confidence": 0.9,
        }
    )
    ev = evaluate_against_ground_truth(
        validated=parsed, validation_ok=True, ground_truth=gt, api_ok=True
    )
    assert ev["evaluation"] == EVAL_EXACT


def test_hallucination_wrong_diameter() -> None:
    gt = derive_ground_truth(
        {
            "raw_text": "4-Y20",
            "semantic_type": "LONGITUDINAL_BAR",
            "reinforcement_role": "UNKNOWN",
            "quantity_status": "EXPLICIT",
            "quantity_value": 4,
            "diameter_value_mm": 20.0,
        }
    )
    parsed = normalize_parsed(
        {
            "candidate_id": "VC::Bx::ANN-y",
            "interpretation_status": STATUS_RESOLVED,
            "semantic_type": "LONGITUDINAL_BAR",
            "role": "UNKNOWN",
            "quantity": 7,
            "diameter_mm": 32,
            "beam_association": "TARGET_BEAM",
            "zone": "UNKNOWN",
            "confidence": 0.9,
        }
    )
    ev = evaluate_against_ground_truth(
        validated=parsed, validation_ok=True, ground_truth=gt, api_ok=True
    )
    assert ev["evaluation"] in (EVAL_HALLUCINATION, "INCORRECT")


def test_prompt_excludes_truth() -> None:
    meta = {
        "candidate_id": "VC::B97A::ANN-d7128f62",
        "beam_id": "B97A",
        "raw_text": "4-Y25",
        "quantity_intent_status": "EXPLICIT",
    }
    prompt = build_user_prompt(meta)
    leaks = assert_no_truth_leak(meta)
    assert not leaks
    assert "expected_role" not in prompt
    assert "ground_truth" not in prompt
    assert "4-Y25" in prompt  # raw text is allowed
    assert "TOP_BAR" not in SYSTEM_PROMPT or "Do not assume" in SYSTEM_PROMPT


def test_shadow_not_production() -> None:
    shadow = build_shadow_result(
        candidate={"candidate_id": "VC::X::Y"},
        claude_interpretation=None,
        validation={"valid": True, "errors": [], "warnings": []},
        conflicts={"flags": []},
        evaluation={"evaluation": "EXACT"},
        comparison={"class": "BOTH_AGREE"},
        evidence_fingerprint="abc",
        prompt_fingerprint="def",
    )
    assert assert_shadow_not_production(shadow)
    assert shadow["production_write"] is False


def test_json_extract() -> None:
    obj, err = extract_json_object('```json\n{"candidate_id": "x", "role": "STIRRUP"}\n```')
    assert err is None
    assert obj["candidate_id"] == "x"


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("longitudinal_oracle", test_longitudinal_oracle),
        ("sfr_oracle_no_invented_quantity", test_sfr_oracle_no_invented_quantity),
        ("stirrup_rejects_quantity", test_stirrup_rejects_quantity),
        ("validator_accepts_longitudinal", test_validator_accepts_longitudinal),
        ("exact_longitudinal_eval", test_exact_longitudinal_eval),
        ("hallucination_wrong_diameter", test_hallucination_wrong_diameter),
        ("prompt_excludes_truth", test_prompt_excludes_truth),
        ("shadow_not_production", test_shadow_not_production),
        ("json_extract", test_json_extract),
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
