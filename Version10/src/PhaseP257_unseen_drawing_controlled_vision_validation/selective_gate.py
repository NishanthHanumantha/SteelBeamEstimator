"""Selective live-shadow gate. Do not send complete unambiguous parses to Claude."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

_OCR_RE = re.compile(r"\\X|\x00")
_SFR_RE = re.compile(r"S\.?F\.?R\.?|SIDE\.?\s*FACE", re.IGNORECASE)


def _ocr(text: str) -> bool:
    return bool(_OCR_RE.search(text or ""))


def _spacing_tokens(text: str) -> List[str]:
    if "@" not in (text or ""):
        return []
    return re.findall(r"\d+", (text or "").split("@", 1)[1])


def trigger_reasons(*, candidate: Dict[str, Any], deterministic: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    text = str(candidate.get("raw_text") or deterministic.get("raw_text") or "")
    stype = deterministic.get("deterministic_type")
    status = deterministic.get("deterministic_status")
    dia = deterministic.get("deterministic_diameter")
    legs = deterministic.get("deterministic_legs")
    spacing = list(deterministic.get("deterministic_spacing") or [])

    if stype in (None, "", "UNKNOWN"):
        reasons.append("TYPE_UNCERTAIN")
    if dia is None and "Y" in text.upper():
        reasons.append("DIAMETER_UNCERTAIN")
    if stype == "STIRRUP" and legs is None:
        reasons.append("LEGS_UNCERTAIN")
    if stype == "STIRRUP" and not spacing:
        reasons.append("SPACING_UNCERTAIN")
    toks = _spacing_tokens(text)
    if spacing and toks and len(toks) > len(spacing):
        reasons.append("SPACING_UNCERTAIN")
    if _ocr(text):
        reasons.append("OCR_UNCERTAIN")
    if _SFR_RE.search(text):
        reasons.append("SIDE_FACE_CANDIDATE")
    if status in ("UNRESOLVED", "INVALID"):
        reasons.append("SEMANTIC_UNCERTAIN")
    # ROLE_UNCERTAIN is recorded but does not alone force a call
    if deterministic.get("deterministic_role") in (None, "UNKNOWN"):
        reasons.append("ROLE_UNCERTAIN")
    seen = []
    for r in reasons:
        if r not in seen:
            seen.append(r)
    return seen


_FORCE_TRIGGERS = {
    "TYPE_UNCERTAIN",
    "DIAMETER_UNCERTAIN",
    "LEGS_UNCERTAIN",
    "SPACING_UNCERTAIN",
    "OCR_UNCERTAIN",
    "SIDE_FACE_CANDIDATE",
    "SEMANTIC_UNCERTAIN",
    "DIFFICULT_VISUAL",
}


def should_invoke_claude(reasons: List[str], *, mode: str = "SELECTIVE_LIVE_SHADOW") -> Tuple[bool, str]:
    if mode == "CONFIGURED_FULL_SHADOW":
        return True, "CONFIGURED_FULL_SHADOW"
    force = [r for r in reasons if r in _FORCE_TRIGGERS]
    if force:
        return True, ",".join(force)
    if reasons == ["ROLE_UNCERTAIN"]:
        return False, "SKIP_ROLE_ONLY_COMPLETE_PARSE"
    return False, "SKIP_DETERMINISTIC_COMPLETE"


__all__ = ["should_invoke_claude", "trigger_reasons"]
