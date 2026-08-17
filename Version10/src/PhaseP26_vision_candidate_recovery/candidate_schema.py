"""P2.6 shadow candidate schema. Runtime: no GT / estimator tokens."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import (
    ASSOCIATIONS,
    CANDIDATE_TYPES,
    CLAUDE_MODEL,
    DECISION_SHADOW,
    DET_UNKNOWN,
    MODEL_VERSION,
    PROMPT_VERSION,
    ROLES,
    SCHEMA_VERSION,
)


def _unk(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, str) and v.strip().upper() in ("UNKNOWN", "NONE", "NULL", ""):
        return None
    return v


def _num(v: Any) -> Optional[float]:
    v = _unk(v)
    if v is None:
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    return n


def _int(v: Any) -> Optional[int]:
    n = _num(v)
    if n is None:
        return None
    return int(round(n))


def _conf(v: Any) -> Optional[float]:
    v = _unk(v)
    if v is None:
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if n < 0 or n > 1:
        return None
    return n


_TYPE_ALIASES = {
    "LONGITUDINAL_BAR": "LONGITUDINAL_REINFORCEMENT",
    "LONGITUDINAL": "LONGITUDINAL_REINFORCEMENT",
    "SIDE_FACE": "SIDE_FACE_REINFORCEMENT",
    "SPACER_BAR": "SPACER",
    "STIRRUP_HOOK": "STIRRUP",
    "TOP_BAR": "LONGITUDINAL_REINFORCEMENT",
    "BOTTOM_BAR": "LONGITUDINAL_REINFORCEMENT",
}
_ROLE_ALIASES = {
    "TOP_MAIN": "TOP_BAR",
    "BOTTOM_MAIN": "BOTTOM_BAR",
    "TOP_EXTRA": "TOP_BAR",
    "BOTTOM_EXTRA": "BOTTOM_BAR",
    "SIDE_FACE_REINFORCEMENT": "SIDE_FACE",
    "SPACER_BAR": "SPACER",
    "STIRRUP_HOOK": "STIRRUP",
    "LONGITUDINAL_REINFORCEMENT": "UNKNOWN",
}


def _enum(v: Any, allowed: tuple, default: str = "UNKNOWN") -> str:
    s = str(_unk(v) or default).strip().upper()
    if allowed is CANDIDATE_TYPES:
        s = _TYPE_ALIASES.get(s, s)
    elif allowed is ROLES:
        s = _ROLE_ALIASES.get(s, s)
    return s if s in allowed else default


def empty_candidate(*, beam_id: str, region_id: str, index: int) -> Dict[str, Any]:
    return {
        "candidate_id": f"P26::{beam_id}::C{index:02d}",
        "source_set": "Fifth Set Drawings",
        "source_drawing": "Fifth Set Drawings",
        "beam_id": beam_id,
        "candidate_type": "UNKNOWN",
        "annotation_text": None,
        "normalized_text": None,
        "role": "UNKNOWN",
        "diameter_mm": None,
        "quantity": None,
        "spacing_mm": [],
        "legs": None,
        "source_x": None,
        "source_y": None,
        "region_id": region_id,
        "region_bbox": None,
        "vision_confidence": None,
        "text_confidence": None,
        "evidence_type": "BEAM_REGION_CROP",
        "evidence_notes": [],
        "deterministic_match_status": DET_UNKNOWN,
        "gt_match_status": None,
        "prompt_version": PROMPT_VERSION,
        "vision_model": CLAUDE_MODEL,
        "model_version": MODEL_VERSION,
        "schema_version": SCHEMA_VERSION,
        "raw_vision_response_reference": None,
        "beam_association": "UNCERTAIN",
        "decision": DECISION_SHADOW,
    }


def normalize_candidate(obj: Dict[str, Any], *, beam_id: str, region_id: str, index: int) -> Dict[str, Any]:
    base = empty_candidate(beam_id=beam_id, region_id=region_id, index=index)
    spacing = obj.get("spacing_mm")
    if spacing is None:
        spacing = []
    if not isinstance(spacing, list):
        spacing = [spacing]
    clean_sp: List[float] = []
    for s in spacing:
        n = _num(s)
        if n is not None:
            clean_sp.append(n)
    notes = obj.get("evidence_notes") or obj.get("evidence_basis") or []
    if isinstance(notes, str):
        notes = [notes]
    loc = obj.get("approx_location") or obj.get("location") or {}
    sx = sy = None
    if isinstance(loc, dict):
        sx = _num(loc.get("x") or loc.get("source_x"))
        sy = _num(loc.get("y") or loc.get("source_y"))
    elif isinstance(loc, str):
        notes = list(notes) + [f"location_text:{loc}"]
    ctype = _enum(obj.get("candidate_type") or obj.get("semantic_type"), CANDIDATE_TYPES)
    role = _enum(obj.get("role"), ROLES)
    if ctype == "STIRRUP" and role == "UNKNOWN":
        role = "STIRRUP"
    text = _unk(obj.get("annotation_text") or obj.get("normalized_notation") or obj.get("normalized_text"))
    base.update(
        {
            "annotation_text": None if text is None else str(text),
            "normalized_text": None if text is None else str(text).strip(),
            "candidate_type": ctype,
            "role": role,
            "diameter_mm": _int(obj.get("diameter_mm")),
            "quantity": _num(obj.get("quantity")),
            "spacing_mm": clean_sp,
            "legs": _int(obj.get("legs")),
            "source_x": sx,
            "source_y": sy,
            "vision_confidence": _conf(obj.get("vision_confidence") or obj.get("confidence")),
            "text_confidence": _conf(obj.get("text_confidence")),
            "evidence_notes": [str(n) for n in notes],
            "beam_association": _enum(obj.get("beam_association"), ASSOCIATIONS, "UNCERTAIN"),
        }
    )
    return base


__all__ = ["empty_candidate", "normalize_candidate"]
