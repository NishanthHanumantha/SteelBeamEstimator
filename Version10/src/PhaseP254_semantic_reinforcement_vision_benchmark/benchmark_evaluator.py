"""Hidden ground-truth evaluation for P2.5.4. Truth is never sent to Claude."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .baseline_comparator import roles_compatible, types_compatible
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

MODEL_VERSION = "10.8.0"


def _num_eq(a: Any, b: Any, tol: float = 1e-6) -> Optional[bool]:
    if a is None or b is None:
        return None
    try:
        return abs(float(a) - float(b)) <= tol
    except Exception:
        return False


def _list_eq(a: Any, b: Any) -> Optional[bool]:
    if not a or not b:
        if not a and not b:
            return True
        if not a or not b:
            return None
    aa = [float(x) for x in a]
    bb = [float(x) for x in b]
    if len(aa) != len(bb):
        return False
    return all(abs(x - y) <= 1e-6 for x, y in zip(aa, bb))


def field_scores(
    validated: Dict[str, Any],
    ground_truth: Dict[str, Any],
) -> Dict[str, Optional[bool]]:
    avail = set(ground_truth.get("fields_available") or [])
    out: Dict[str, Optional[bool]] = {
        "type": None,
        "role": None,
        "quantity": None,
        "diameter": None,
        "spacing": None,
        "beam_association": None,
        "zone": None,
    }
    if "semantic_type" in avail:
        out["type"] = types_compatible(
            validated.get("semantic_type"), ground_truth.get("semantic_type")
        )
    if "role" in avail and ground_truth.get("role") not in (None, "UNKNOWN"):
        pred = validated.get("role")
        if pred in (None, "UNKNOWN"):
            out["role"] = False
        else:
            out["role"] = roles_compatible(pred, ground_truth.get("role"))
    if "quantity" in avail and ground_truth.get("quantity") is not None:
        out["quantity"] = _num_eq(validated.get("quantity"), ground_truth.get("quantity"))
        if out["quantity"] is None:
            out["quantity"] = False
    if "diameter_mm" in avail and ground_truth.get("diameter_mm") is not None:
        out["diameter"] = _num_eq(validated.get("diameter_mm"), ground_truth.get("diameter_mm"))
        if out["diameter"] is None:
            out["diameter"] = False
    if "spacing_mm" in avail and ground_truth.get("spacing_mm"):
        out["spacing"] = _list_eq(validated.get("spacing_mm"), ground_truth.get("spacing_mm"))
        if out["spacing"] is None:
            out["spacing"] = False
    if "beam_association" in avail and ground_truth.get("beam_association"):
        pred = validated.get("beam_association")
        gt = ground_truth.get("beam_association")
        if pred == "UNCERTAIN":
            out["beam_association"] = False
        else:
            out["beam_association"] = pred == gt
    if "zone" in avail and ground_truth.get("zone") not in (None, "UNKNOWN"):
        pred = validated.get("zone")
        if pred in (None, "UNKNOWN"):
            out["zone"] = False
        else:
            out["zone"] = pred == ground_truth.get("zone")
    return out


def evaluate_against_ground_truth(
    *,
    validated: Optional[Dict[str, Any]],
    validation_ok: bool,
    ground_truth: Dict[str, Any],
    api_ok: bool,
    evidence_weak: bool = False,
) -> Dict[str, Any]:
    if not api_ok:
        return {"evaluation": EVAL_API_ERROR, "exact_match": False, "field_scores": {}}
    if not validation_ok or not validated:
        return {
            "evaluation": EVAL_INVALID_RESPONSE,
            "exact_match": False,
            "field_scores": {},
        }

    status = validated.get("interpretation_status")
    scored = field_scores(validated, ground_truth) if ground_truth.get("available") else {}
    comparable = {k: v for k, v in scored.items() if v is not None}
    true_n = sum(1 for v in comparable.values() if v)
    false_n = sum(1 for v in comparable.values() if v is False)

    if status == STATUS_CONFLICT:
        return {
            "evaluation": EVAL_CONFLICT_DETECTED,
            "exact_match": False,
            "field_scores": scored,
        }

    if not ground_truth.get("available"):
        return {
            "evaluation": EVAL_GT_UNAVAILABLE,
            "exact_match": False,
            "field_scores": scored,
        }

    numeric_gt = any(
        f in (ground_truth.get("fields_available") or [])
        for f in ("quantity", "diameter_mm", "spacing_mm", "legs")
    )

    if status == STATUS_INSUFFICIENT:
        # Appropriate if evidence is weak or numeric GT is not expected (SFR / notes)
        if evidence_weak or not numeric_gt:
            return {
                "evaluation": EVAL_APPROPRIATE_ABSTENTION,
                "exact_match": False,
                "field_scores": scored,
            }
        return {
            "evaluation": EVAL_APPROPRIATE_ABSTENTION
            if false_n == 0 and true_n == 0
            else EVAL_PARTIAL,
            "exact_match": False,
            "field_scores": scored,
            "details": "abstained_on_available_gt",
        }

    if status == STATUS_RESOLVED and false_n > 0 and true_n == 0:
        return {
            "evaluation": EVAL_HALLUCINATION,
            "exact_match": False,
            "field_scores": scored,
            "details": "resolved_with_unsupported_values",
        }

    if status == STATUS_RESOLVED and false_n == 0 and true_n > 0:
        # All comparable GT fields match
        return {
            "evaluation": EVAL_EXACT,
            "exact_match": True,
            "field_scores": scored,
        }

    if status in (STATUS_RESOLVED, STATUS_PARTIAL) and true_n > 0 and false_n > 0:
        if status == STATUS_RESOLVED and scored.get("type") is False:
            return {
                "evaluation": EVAL_HALLUCINATION,
                "exact_match": False,
                "field_scores": scored,
                "details": "resolved_wrong_semantic_type",
            }
        return {
            "evaluation": EVAL_INCORRECT if status == STATUS_RESOLVED else EVAL_PARTIAL,
            "exact_match": False,
            "field_scores": scored,
        }

    if status == STATUS_PARTIAL and true_n > 0 and false_n == 0:
        return {
            "evaluation": EVAL_PARTIAL,
            "exact_match": False,
            "field_scores": scored,
        }

    if status == STATUS_RESOLVED and false_n > 0:
        return {
            "evaluation": EVAL_INCORRECT,
            "exact_match": False,
            "field_scores": scored,
        }

    if status == STATUS_PARTIAL:
        return {
            "evaluation": EVAL_PARTIAL,
            "exact_match": False,
            "field_scores": scored,
        }

    return {
        "evaluation": EVAL_GT_UNAVAILABLE if not comparable else EVAL_INCORRECT,
        "exact_match": False,
        "field_scores": scored,
    }


__all__ = ["evaluate_against_ground_truth", "field_scores"]
