"""
Hidden ground-truth derivation + evaluation for P2.5.3.

Ground truth is NEVER sent to Claude.
For OCR-corrupted stirrup candidates, truth is derived by removing the
OCR control token \\X and parsing the cleaned notation deterministically.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .config import (
    EVAL_API_ERROR,
    EVAL_APPROPRIATE_ABSTENTION,
    EVAL_CONFLICT_DETECTED,
    EVAL_EXACT,
    EVAL_GT_UNAVAILABLE,
    EVAL_HALLUCINATION,
    EVAL_INCORRECT,
    EVAL_INVALID_RESPONSE,
    EVAL_PARTIAL,
    STATUS_CONFLICT,
    STATUS_INSUFFICIENT,
    STATUS_PARTIAL,
    STATUS_RESOLVED,
)

MODEL_VERSION = "10.7.0"

_STIRRUP_RE = re.compile(
    r"(?P<legs>\d+)\s*L?\s*-?\s*Y(?P<dia>\d+(?:\.\d+)?)\s*@"
    r"(?P<spacings>\d+(?:\s*/\s*\d+)*)\s*(?:C/?C)?",
    re.IGNORECASE,
)


def derive_ground_truth(raw_text: str, reason_codes: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Evaluation-only oracle. Not exposed to Claude.
    """
    reasons = set(reason_codes or [])
    raw = raw_text or ""
    # OCR control sequence cleanup for evaluation oracle only
    cleaned = raw.replace("\\X", "").replace("\x00", "").strip()
    cleaned = re.sub(r"\s+", "", cleaned)

    m = _STIRRUP_RE.search(cleaned)
    if m:
        legs = int(m.group("legs"))
        dia = float(m.group("dia"))
        spacings = [int(x) for x in re.findall(r"\d+", m.group("spacings"))]
        pattern = "VARIABLE" if len(spacings) > 1 else "UNIFORM"
        notation = f"{legs}L-Y{int(dia) if dia == int(dia) else dia}@" + "/".join(
            str(s) for s in spacings
        ) + "C/C"
        return {
            "available": True,
            "source": "OCR_CLEAN_STIRRUP_ORACLE",
            "reinforcement_type": "STIRRUP",
            "legs": legs,
            "diameter_mm": dia,
            "spacing_mm": spacings,
            "spacing_pattern": pattern,
            "quantity": None,
            "normalized_notation": notation,
            "raw_text": raw,
            "cleaned_text": cleaned,
            "ocr_case": "OCR_CORRUPTION" in reasons or "\\X" in raw,
        }

    return {
        "available": False,
        "source": "NONE",
        "raw_text": raw,
        "reason": "GROUND_TRUTH_UNAVAILABLE",
    }


def _nums_equal(a: Any, b: Any, tol: float = 1e-6) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except Exception:
        return False


def _list_equal(a: List[Any], b: List[Any]) -> bool:
    if len(a) != len(b):
        return False
    return all(_nums_equal(x, y) for x, y in zip(a, b))


def evaluate_against_ground_truth(
    *,
    validated: Optional[Dict[str, Any]],
    validation_ok: bool,
    ground_truth: Dict[str, Any],
    api_ok: bool,
) -> Dict[str, Any]:
    if not api_ok:
        return {
            "evaluation": EVAL_API_ERROR,
            "exact_match": False,
            "details": "claude_api_failed",
        }
    if not validation_ok or not validated:
        return {
            "evaluation": EVAL_INVALID_RESPONSE,
            "exact_match": False,
            "details": "schema_or_engineering_validation_failed",
        }

    status = validated.get("interpretation_status")
    if not ground_truth.get("available"):
        # Without GT: only score abstention quality heuristically
        if status in (STATUS_INSUFFICIENT, STATUS_PARTIAL, STATUS_CONFLICT):
            return {
                "evaluation": EVAL_GT_UNAVAILABLE,
                "exact_match": False,
                "details": "no_gt_abstention_or_partial_recorded",
            }
        return {
            "evaluation": EVAL_GT_UNAVAILABLE,
            "exact_match": False,
            "details": "no_gt_resolved_unscored",
        }

    gt_type = ground_truth.get("reinforcement_type")
    pred_type = validated.get("reinforcement_type")

    if status == STATUS_CONFLICT:
        return {
            "evaluation": EVAL_CONFLICT_DETECTED,
            "exact_match": False,
            "details": "model_reported_conflict",
        }

    if status == STATUS_INSUFFICIENT:
        # For OCR cases with clear visual notation, abstention is weak but still "appropriate"
        # if evidence was marked incomplete upstream — treat as appropriate abstention.
        return {
            "evaluation": EVAL_APPROPRIATE_ABSTENTION,
            "exact_match": False,
            "details": "model_abstained",
        }

    # Hallucination: claims RESOLVED with wrong type or invented fields unsupported by GT pattern
    if status == STATUS_RESOLVED and pred_type not in (gt_type, "UNKNOWN"):
        return {
            "evaluation": EVAL_HALLUCINATION,
            "exact_match": False,
            "details": "resolved_wrong_reinforcement_type",
        }

    if gt_type == "STIRRUP":
        legs_ok = validated.get("legs") is None or int(validated.get("legs")) == int(
            ground_truth["legs"]
        )
        dia_ok = _nums_equal(validated.get("diameter_mm"), ground_truth["diameter_mm"])
        sp_ok = _list_equal(
            [float(x) for x in (validated.get("spacing_mm") or [])],
            [float(x) for x in (ground_truth.get("spacing_mm") or [])],
        )
        qty_bad = validated.get("quantity") is not None

        if status == STATUS_RESOLVED and dia_ok and sp_ok and legs_ok and not qty_bad:
            return {
                "evaluation": EVAL_EXACT,
                "exact_match": True,
                "details": {
                    "legs_ok": legs_ok,
                    "diameter_ok": dia_ok,
                    "spacing_ok": sp_ok,
                },
            }
        if status in (STATUS_RESOLVED, STATUS_PARTIAL) and (dia_ok or sp_ok or legs_ok):
            # Some components correct
            if status == STATUS_RESOLVED and (not dia_ok or not sp_ok):
                return {
                    "evaluation": EVAL_INCORRECT,
                    "exact_match": False,
                    "details": {
                        "legs_ok": legs_ok,
                        "diameter_ok": dia_ok,
                        "spacing_ok": sp_ok,
                        "qty_bad": qty_bad,
                    },
                }
            return {
                "evaluation": EVAL_PARTIAL,
                "exact_match": False,
                "details": {
                    "legs_ok": legs_ok,
                    "diameter_ok": dia_ok,
                    "spacing_ok": sp_ok,
                },
            }
        if status == STATUS_RESOLVED and not (dia_ok or sp_ok):
            return {
                "evaluation": EVAL_HALLUCINATION,
                "exact_match": False,
                "details": "resolved_with_unsupported_values",
            }
        return {
            "evaluation": EVAL_INCORRECT,
            "exact_match": False,
            "details": {
                "legs_ok": legs_ok,
                "diameter_ok": dia_ok,
                "spacing_ok": sp_ok,
            },
        }

    return {
        "evaluation": EVAL_GT_UNAVAILABLE,
        "exact_match": False,
        "details": "unsupported_gt_type",
    }


__all__ = ["derive_ground_truth", "evaluate_against_ground_truth"]
