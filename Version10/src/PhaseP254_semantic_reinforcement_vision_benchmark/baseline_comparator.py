"""Compare Claude shadow interpretation vs deterministic P2.5.1 baseline."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import (
    CMP_BOTH_AGREE,
    CMP_DETERMINISTIC_CONFLICT,
    CMP_DETERMINISTIC_RESOLVED,
    CMP_GT_UNAVAILABLE,
    CMP_VISION_ABSTAINED,
    CMP_VISION_CONFLICT,
    CMP_VISION_ONLY_RESOLVED,
    CMP_VISION_WRONG,
    STATUS_CONFLICT,
    STATUS_INSUFFICIENT,
    STATUS_PARTIAL,
    STATUS_RESOLVED,
)

MODEL_VERSION = "10.8.0"


def _num_eq(a: Any, b: Any, tol: float = 1e-6) -> bool:
    if a is None or b is None:
        return a is None and b is None
    try:
        return abs(float(a) - float(b)) <= tol
    except Exception:
        return False


def _list_eq(a: Any, b: Any) -> bool:
    aa = [float(x) for x in (a or [])]
    bb = [float(x) for x in (b or [])]
    if len(aa) != len(bb):
        return False
    return all(_num_eq(x, y) for x, y in zip(aa, bb))


def types_compatible(pred: Optional[str], gt: Optional[str]) -> bool:
    if pred is None or gt is None:
        return False
    aliases = {
        "SIDE_FACE": "SIDE_FACE_REINFORCEMENT",
        "SIDE_FACE_REINFORCEMENT": "SIDE_FACE_REINFORCEMENT",
        "SUPPORT_REINFORCEMENT": "LONGITUDINAL_BAR",
    }
    return aliases.get(pred, pred) == aliases.get(gt, gt) or pred == gt


def roles_compatible(pred: Optional[str], gt: Optional[str]) -> bool:
    if not pred or not gt or gt == "UNKNOWN":
        return False
    if pred == gt:
        return True
    aliases = {
        ("SUPPORT_TOP", "TOP_BAR"),
        ("TOP_BAR", "SUPPORT_TOP"),
        ("SUPPORT_BOTTOM", "BOTTOM_BAR"),
        ("BOTTOM_BAR", "SUPPORT_BOTTOM"),
        ("SIDE_FACE", "SIDE_FACE"),
    }
    return (pred, gt) in aliases


def collect_conflicts(
    *,
    validated: Optional[Dict[str, Any]],
    candidate: Dict[str, Any],
    ground_truth: Dict[str, Any],
) -> Dict[str, Any]:
    flags: List[str] = []
    if not validated:
        return {"flags": flags, "details": {}}
    details: Dict[str, Any] = {}
    pred_dia = validated.get("diameter_mm")
    base_dia = candidate.get("baseline_diameter_mm")
    if pred_dia is not None and base_dia is not None and not _num_eq(pred_dia, base_dia):
        flags.append("DIAMETER_CONFLICT")
        details["diameter"] = {"claude": pred_dia, "deterministic": base_dia}

    pred_role = validated.get("role")
    base_role = candidate.get("baseline_role")
    if (
        pred_role
        and pred_role != "UNKNOWN"
        and base_role
        and base_role != "UNKNOWN"
        and not roles_compatible(pred_role, base_role)
    ):
        flags.append("ROLE_CONFLICT")
        details["role"] = {"claude": pred_role, "deterministic": base_role}

    pred_assoc = validated.get("beam_association")
    if pred_assoc == "OTHER_BEAM" and (ground_truth.get("beam_association") == "TARGET_BEAM"):
        flags.append("OWNERSHIP_CONFLICT")
        details["beam_association"] = {
            "claude": pred_assoc,
            "deterministic": "TARGET_BEAM",
        }
    return {"flags": flags, "details": details}


def compare_baseline(
    *,
    candidate: Dict[str, Any],
    validated: Optional[Dict[str, Any]],
    validation_ok: bool,
    ground_truth: Dict[str, Any],
    evaluation: Dict[str, Any],
) -> Dict[str, Any]:
    baseline_resolved = bool(candidate.get("baseline_resolved"))
    status = (validated or {}).get("interpretation_status")
    eval_code = evaluation.get("evaluation")
    gt_ok = bool(ground_truth.get("available"))

    if not gt_ok:
        cls = CMP_GT_UNAVAILABLE
    elif status in (STATUS_INSUFFICIENT, None) or eval_code == "APPROPRIATE_ABSTENTION":
        cls = CMP_VISION_ABSTAINED
    elif status == STATUS_CONFLICT or eval_code == "CONFLICT_DETECTED":
        cls = CMP_VISION_CONFLICT
    elif eval_code in ("INCORRECT", "HALLUCINATION", "INVALID_RESPONSE", "API_ERROR"):
        cls = CMP_VISION_WRONG
        if baseline_resolved:
            cls = CMP_VISION_WRONG
    elif eval_code in ("EXACT", "PARTIAL") and not baseline_resolved:
        cls = CMP_VISION_ONLY_RESOLVED
    elif eval_code in ("EXACT", "PARTIAL") and baseline_resolved:
        cls = CMP_BOTH_AGREE
    elif baseline_resolved:
        cls = CMP_DETERMINISTIC_RESOLVED
    else:
        cls = CMP_DETERMINISTIC_CONFLICT

    return {
        "class": cls,
        "baseline_resolved": baseline_resolved,
        "vision_status": status,
        "evaluation": eval_code,
        "validation_ok": validation_ok,
    }


__all__ = [
    "collect_conflicts",
    "compare_baseline",
    "roles_compatible",
    "types_compatible",
]
