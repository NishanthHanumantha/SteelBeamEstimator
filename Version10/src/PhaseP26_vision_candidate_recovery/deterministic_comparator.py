"""Compare Vision shadow candidates to deterministic R1.3 reinforcement. No GT."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .config import DET_ALREADY, DET_CONFLICT, DET_MISSING, DET_UNKNOWN

_ROLE_FAMILY = {
    "TOP_BAR": "TOP",
    "TOP_MAIN": "TOP",
    "TOP_EXTRA": "TOP",
    "BOTTOM_BAR": "BOTTOM",
    "BOTTOM_MAIN": "BOTTOM",
    "BOTTOM_EXTRA": "BOTTOM",
    "STIRRUP": "STIRRUP",
    "STIRRUP_HOOK": "STIRRUP",
    "SIDE_FACE": "SIDE",
    "SIDE_FACE_REINFORCEMENT": "SIDE",
    "SPACER": "SPACER",
    "SPACER_BAR": "SPACER",
    "ADDITIONAL": "OTHER",
    "UNKNOWN": "UNKNOWN",
}


def role_family(role: Any) -> str:
    return _ROLE_FAMILY.get(str(role or "UNKNOWN").strip().upper(), "OTHER")


def _norm_text(text: Any) -> str:
    s = re.sub(r"\s+", "", str(text or "").upper())
    s = s.replace("\\X", "")
    return s


def _dia(v: Any) -> Optional[int]:
    try:
        n = int(round(float(v)))
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def flatten_r13(model: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not model:
        return []
    keys = (
        ("top_main_bars", "TOP"),
        ("top_extra_bars", "TOP"),
        ("bottom_main_bars", "BOTTOM"),
        ("bottom_extra_bars", "BOTTOM"),
        ("stirrups", "STIRRUP"),
        ("side_face_reinforcement", "SIDE"),
        ("spacer_bars", "SPACER"),
        ("supplementary_bars", "OTHER"),
    )
    out: List[Dict[str, Any]] = []
    for key, fam in keys:
        for b in model.get(key) or []:
            if not isinstance(b, dict):
                continue
            fam2 = role_family(b.get("semantic_role")) or fam
            if fam2 in ("UNKNOWN", "OTHER"):
                fam2 = fam
            out.append(
                {
                    "bar_id": b.get("bar_id"),
                    "family": fam2,
                    "diameter_mm": _dia(b.get("diameter_mm")),
                    "quantity": b.get("quantity"),
                    "bar_label": b.get("bar_label"),
                    "norm_label": _norm_text(b.get("bar_label")),
                }
            )
    return out


def compare_candidate(
    candidate: Dict[str, Any],
    *,
    r13_model: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    assoc = str(candidate.get("beam_association") or "UNCERTAIN")
    if assoc == "OTHER_BEAM":
        return {
            "deterministic_match_status": DET_UNKNOWN,
            "match_reason": "OTHER_BEAM_ASSOCIATION",
            "matched_bar_id": None,
        }
    bars = flatten_r13(r13_model)
    fam = role_family(candidate.get("role"))
    dia = _dia(candidate.get("diameter_mm"))
    text = _norm_text(candidate.get("normalized_text") or candidate.get("annotation_text"))
    if fam == "UNKNOWN" and dia is None and not text:
        return {
            "deterministic_match_status": DET_UNKNOWN,
            "match_reason": "INSUFFICIENT_VISION_FIELDS",
            "matched_bar_id": None,
        }

    same_fam_dia: List[Dict[str, Any]] = []
    same_fam_diff_dia: List[Dict[str, Any]] = []
    text_hits: List[Dict[str, Any]] = []
    for b in bars:
        text_ok = bool(text) and text == b["norm_label"] and len(text) >= 4
        fam_ok = fam != "UNKNOWN" and b["family"] == fam
        dia_ok = dia is not None and b["diameter_mm"] is not None and dia == b["diameter_mm"]
        if fam_ok and dia_ok:
            same_fam_dia.append(b)
        elif fam_ok and dia is not None and b["diameter_mm"] is not None:
            same_fam_diff_dia.append(b)
        if text_ok and (fam_ok or fam == "UNKNOWN"):
            text_hits.append(b)

    if same_fam_dia:
        hit = same_fam_dia[0]
        return {
            "deterministic_match_status": DET_ALREADY,
            "match_reason": "ROLE_FAMILY_AND_DIAMETER",
            "matched_bar_id": hit.get("bar_id"),
        }
    if text_hits and (fam == "UNKNOWN" or role_family(text_hits[0].get("family")) == fam or text_hits[0]["family"] == fam):
        hit = text_hits[0]
        return {
            "deterministic_match_status": DET_ALREADY,
            "match_reason": "ANNOTATION_TEXT_AND_CONTEXT",
            "matched_bar_id": hit.get("bar_id"),
        }
    if same_fam_diff_dia and dia is not None:
        return {
            "deterministic_match_status": DET_CONFLICT,
            "match_reason": "SAME_ROLE_DIFFERENT_DIAMETER",
            "matched_bar_id": same_fam_diff_dia[0].get("bar_id"),
        }
    return {
        "deterministic_match_status": DET_MISSING,
        "match_reason": "NO_EQUIVALENT_DETERMINISTIC_BAR",
        "matched_bar_id": None,
    }


def apply_comparison(
    candidates: List[Dict[str, Any]],
    *,
    r13_model: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    out = []
    for cand in candidates:
        rec = dict(cand)
        cmp = compare_candidate(rec, r13_model=r13_model)
        rec["deterministic_match_status"] = cmp["deterministic_match_status"]
        rec["deterministic_match_reason"] = cmp["match_reason"]
        rec["deterministic_matched_bar_id"] = cmp["matched_bar_id"]
        rec["decision"] = "SHADOW_CANDIDATE"
        out.append(rec)
    return out


__all__ = ["apply_comparison", "compare_candidate", "flatten_r13", "role_family"]
