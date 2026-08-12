"""Unit tests for P2.5.3 (no live Claude calls)."""
from __future__ import annotations

from typing import Any, Dict, List

from .benchmark_evaluator import derive_ground_truth, evaluate_against_ground_truth
from .config import EVAL_EXACT, EVAL_HALLUCINATION, STATUS_RESOLVED
from .interpretation_validator import validate_interpretation
from .response_schema import extract_json_object, normalize_parsed

MODEL_VERSION = "10.7.0"


def test_ocr_ground_truth_oracle() -> None:
    gt = derive_ground_truth(r"4L-Y12@\X100C/C", ["OCR_CORRUPTION"])
    assert gt["available"] is True
    assert gt["legs"] == 4
    assert gt["diameter_mm"] == 12
    assert gt["spacing_mm"] == [100]


def test_variable_spacing_oracle() -> None:
    gt = derive_ground_truth(r"4L-Y10@\X100/150/100C/C", ["OCR_CORRUPTION"])
    assert gt["available"]
    assert gt["spacing_mm"] == [100, 150, 100]
    assert gt["spacing_pattern"] == "VARIABLE"


def test_validator_rejects_stirrup_quantity() -> None:
    parsed = normalize_parsed(
        {
            "candidate_id": "VC::B129::ANN-7aec78cb",
            "interpretation_status": STATUS_RESOLVED,
            "reinforcement_type": "STIRRUP",
            "quantity": 4,
            "diameter_mm": 12,
            "legs": 4,
            "spacing_mm": [100],
            "spacing_pattern": "UNIFORM",
            "normalized_notation": "4L-Y12@100C/C",
            "confidence": 0.9,
            "visual_evidence": ["text"],
            "reasoning_summary": "x",
            "warnings": [],
        }
    )
    v = validate_interpretation(parsed=parsed, expected_candidate_id="VC::B129::ANN-7aec78cb")
    assert v["valid"] is False
    assert "STIRRUP_MUST_NOT_HAVE_LONGITUDINAL_QUANTITY" in v["errors"]


def test_validator_accepts_stirrup() -> None:
    parsed = normalize_parsed(
        {
            "candidate_id": "VC::B129::ANN-7aec78cb",
            "interpretation_status": STATUS_RESOLVED,
            "reinforcement_type": "STIRRUP",
            "quantity": None,
            "diameter_mm": 12,
            "legs": 4,
            "spacing_mm": [100],
            "spacing_pattern": "UNIFORM",
            "normalized_notation": "4L-Y12@100C/C",
            "confidence": 0.9,
            "visual_evidence": ["magenta text"],
            "reasoning_summary": "ocr fix",
            "warnings": [],
        }
    )
    v = validate_interpretation(parsed=parsed, expected_candidate_id="VC::B129::ANN-7aec78cb")
    assert v["valid"] is True


def test_exact_evaluation() -> None:
    gt = derive_ground_truth(r"4L-Y12@\X100C/C", ["OCR_CORRUPTION"])
    validated = {
        "interpretation_status": STATUS_RESOLVED,
        "reinforcement_type": "STIRRUP",
        "legs": 4,
        "diameter_mm": 12,
        "spacing_mm": [100],
        "quantity": None,
    }
    ev = evaluate_against_ground_truth(
        validated=validated, validation_ok=True, ground_truth=gt, api_ok=True
    )
    assert ev["evaluation"] == EVAL_EXACT


def test_hallucination_wrong_values() -> None:
    gt = derive_ground_truth(r"4L-Y12@\X100C/C", ["OCR_CORRUPTION"])
    validated = {
        "interpretation_status": STATUS_RESOLVED,
        "reinforcement_type": "STIRRUP",
        "legs": 2,
        "diameter_mm": 25,
        "spacing_mm": [200],
        "quantity": None,
    }
    ev = evaluate_against_ground_truth(
        validated=validated, validation_ok=True, ground_truth=gt, api_ok=True
    )
    assert ev["evaluation"] in (EVAL_HALLUCINATION, "INCORRECT")


def test_json_extract() -> None:
    obj, err = extract_json_object('```json\n{"candidate_id":"X","interpretation_status":"PARTIAL"}\n```')
    assert err is None
    assert obj["candidate_id"] == "X"


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("ocr_ground_truth_oracle", test_ocr_ground_truth_oracle),
        ("variable_spacing_oracle", test_variable_spacing_oracle),
        ("validator_rejects_stirrup_quantity", test_validator_rejects_stirrup_quantity),
        ("validator_accepts_stirrup", test_validator_accepts_stirrup),
        ("exact_evaluation", test_exact_evaluation),
        ("hallucination_wrong_values", test_hallucination_wrong_values),
        ("json_extract", test_json_extract),
    ]
    results: List[Dict[str, Any]] = []
    for name, fn in tests:
        try:
            fn()
            results.append({"name": name, "pass": True})
        except Exception as exc:  # noqa: BLE001
            results.append({"name": name, "pass": False, "error": str(exc)})
    passed = sum(1 for r in results if r.get("pass"))
    return {
        "success": passed == len(results),
        "passed": passed,
        "total": len(results),
        "results": results,
        "model_version": MODEL_VERSION,
    }


__all__ = ["run_unit_tests"]
