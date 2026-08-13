"""Operational comparison of deterministic vs Vision — GT overlay is separate."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PhaseP254_semantic_reinforcement_vision_benchmark.baseline_comparator import (
    roles_compatible,
    types_compatible,
)
from PhaseP254_semantic_reinforcement_vision_benchmark.config import (
    STATUS_INSUFFICIENT,
    STATUS_PARTIAL,
    STATUS_RESOLVED,
)

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
    IMPORTANT_FIELDS,
)


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
    return all(abs(x - y) <= 1e-6 for x, y in zip(aa, bb))


def vision_is_resolved(vision: Optional[Dict[str, Any]], validation_ok: bool) -> bool:
    if not validation_ok or not vision:
        return False
    return vision.get("interpretation_status") == STATUS_RESOLVED


def vision_is_partial(vision: Optional[Dict[str, Any]], validation_ok: bool) -> bool:
    if not validation_ok or not vision:
        return False
    return vision.get("interpretation_status") == STATUS_PARTIAL


def collect_important_conflicts(
    *,
    deterministic: Dict[str, Any],
    vision: Optional[Dict[str, Any]],
) -> Tuple[List[str], Dict[str, Any]]:
    """Field-level disagreements where BOTH sides have a resolved value. Zone is excluded."""
    flags: List[str] = []
    details: Dict[str, Any] = {}
    if not vision:
        return flags, details

    v_type = vision.get("semantic_type")
    d_type = deterministic.get("deterministic_type")
    if (
        deterministic.get("deterministic_type_resolved")
        and v_type not in (None, "UNKNOWN")
        and not types_compatible(v_type, d_type)
    ):
        flags.append("type")
        details["type"] = {"vision": v_type, "deterministic": d_type}

    v_role = vision.get("role")
    d_role = deterministic.get("deterministic_role")
    if (
        deterministic.get("deterministic_role_resolved")
        and v_role not in (None, "UNKNOWN")
        and not roles_compatible(v_role, d_role)
        and not (v_role == d_role)
    ):
        flags.append("role")
        details["role"] = {"vision": v_role, "deterministic": d_role}

    v_dia = vision.get("diameter_mm")
    d_dia = deterministic.get("deterministic_diameter")
    if v_dia is not None and d_dia is not None and not _num_eq(v_dia, d_dia):
        flags.append("diameter")
        details["diameter"] = {"vision": v_dia, "deterministic": d_dia}

    v_qty = vision.get("quantity")
    d_qty = deterministic.get("deterministic_quantity")
    if v_qty is not None and d_qty is not None and not _num_eq(v_qty, d_qty):
        flags.append("quantity")
        details["quantity"] = {"vision": v_qty, "deterministic": d_qty}

    v_sp = vision.get("spacing_mm") or []
    d_sp = deterministic.get("deterministic_spacing") or []
    if v_sp and d_sp and not _list_eq(v_sp, d_sp):
        flags.append("spacing")
        details["spacing"] = {"vision": v_sp, "deterministic": d_sp}

    v_assoc = vision.get("beam_association")
    d_assoc = deterministic.get("deterministic_association")
    if (
        v_assoc in ("TARGET_BEAM", "OTHER_BEAM")
        and d_assoc in ("TARGET_BEAM", "OTHER_BEAM")
        and v_assoc != d_assoc
    ):
        flags.append("beam_association")
        details["beam_association"] = {"vision": v_assoc, "deterministic": d_assoc}

    # zone is diagnostic only — never an operational conflict
    _ = IMPORTANT_FIELDS
    return flags, details


def classify_operational(
    *,
    deterministic: Dict[str, Any],
    vision: Optional[Dict[str, Any]],
    validation_ok: bool,
    conflict_fields: List[str],
) -> str:
    v_res = vision_is_resolved(vision, validation_ok)
    v_partial = vision_is_partial(vision, validation_ok)
    v_useful = v_res or v_partial
    det_full = bool(deterministic.get("deterministic_resolved"))
    det_type = bool(deterministic.get("deterministic_type_resolved"))

    if conflict_fields:
        return CMP_VISION_CONFLICT
    if v_useful and det_type:
        # Type/role present on both and no field conflicts → agreement,
        # including OCR-difficult stirrups whose numeric parse is unresolved.
        return CMP_BOTH_AGREE
    if v_res and not det_type:
        return CMP_VISION_ONLY_RESOLVED
    if (det_full or det_type) and not v_useful:
        return CMP_DETERMINISTIC_ONLY_RESOLVED
    if v_res and not det_full and not det_type:
        return CMP_VISION_ONLY_RESOLVED
    return CMP_BOTH_UNRESOLVED


def apply_gt_overlay(
    *,
    operational_class: str,
    evaluation: Optional[Dict[str, Any]],
) -> Tuple[str, str]:
    """VISION_WRONG is evaluation-only. Do not confuse with VISION_CONFLICT."""
    code = (evaluation or {}).get("evaluation")
    if code in ("HALLUCINATION", "INCORRECT"):
        return CMP_VISION_WRONG, ACT_KEEP_DET_VISION_ERROR
    action = {
        CMP_BOTH_AGREE: ACT_KEEP_DET,
        CMP_VISION_ONLY_RESOLVED: ACT_SHADOW_VISION,
        CMP_DETERMINISTIC_ONLY_RESOLVED: ACT_KEEP_DET,
        CMP_VISION_CONFLICT: ACT_KEEP_DET_CONFLICT,
        CMP_BOTH_UNRESOLVED: ACT_UNRESOLVED,
    }.get(operational_class, ACT_KEEP_DET)
    return operational_class, action


def promotion_eligible_flag(
    *,
    comparison_class: str,
    operational_class: str,
    validation_ok: bool,
    safety: Dict[str, Any],
) -> bool:
    """Diagnostic only. Never authorizes a production write."""
    if comparison_class == CMP_VISION_WRONG:
        return False
    if operational_class != CMP_VISION_ONLY_RESOLVED:
        return False
    if not validation_ok or safety.get("vision_rejected"):
        return False
    if safety.get("production_write"):
        return False
    return True


def vision_status_label(
    vision: Optional[Dict[str, Any]],
    validation_ok: bool,
    api_ok: bool,
) -> str:
    if not api_ok:
        return "API_ERROR"
    if not validation_ok or not vision:
        return "INVALID_OR_ABSTAINED"
    return str(vision.get("interpretation_status") or STATUS_INSUFFICIENT)


__all__ = [
    "apply_gt_overlay",
    "classify_operational",
    "collect_important_conflicts",
    "promotion_eligible_flag",
    "vision_is_resolved",
    "vision_status_label",
]
