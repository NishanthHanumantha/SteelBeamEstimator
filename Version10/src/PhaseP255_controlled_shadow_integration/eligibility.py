"""Selective Claude invocation gate. P2.5.5 default is CONFIGURED_FULL_SHADOW."""
from __future__ import annotations

from typing import Any, Dict, List

from .config import DEFAULT_ELIGIBILITY


def eligibility_reasons(
    *,
    candidate: Dict[str, Any],
    deterministic: Dict[str, Any],
    mode: str = DEFAULT_ELIGIBILITY,
) -> List[str]:
    """Return all matching trigger reasons. Does not decide whether to call Claude."""
    reasons: List[str] = []
    codes = set(candidate.get("candidate_reason_codes") or [])
    tags = set(candidate.get("semantic_class_tags") or [])
    cls = candidate.get("semantic_class")
    text = str(candidate.get("raw_text") or "")

    if "OCR_CORRUPTION" in codes or "OCR_CONTROL" in tags or cls == "OCR_CONTROL":
        reasons.append("OCR_UNCERTAIN")
    if (
        "UNRESOLVED_QUANTITY" in codes
        or "STIRRUP_PATTERN_UNPARSED" in codes
        or deterministic.get("deterministic_status") in ("UNRESOLVED", "INVALID", None)
    ):
        reasons.append("SEMANTIC_UNCERTAIN")
    if deterministic.get("deterministic_role") in (None, "UNKNOWN"):
        reasons.append("ROLE_UNCERTAIN")
    if deterministic.get("deterministic_type") in (None, "UNKNOWN"):
        reasons.append("TYPE_UNCERTAIN")
    if "BEAM_ASSOCIATION" in tags:
        reasons.append("BEAM_ASSOCIATION_UNCERTAIN")
    if "DIFFICULT_VISUAL" in tags or cls == "DIFFICULT_VISUAL":
        reasons.append("DIFFICULT_VISUAL")
    if (
        "SIDE_FACE" in tags
        or cls == "SIDE_FACE"
        or "S.F" in text.upper()
        or "SFR" in text.upper()
    ):
        reasons.append("SIDE_FACE_CANDIDATE")
    if "MULTI_ANNOTATION" in tags or cls == "MULTI_ANNOTATION":
        reasons.append("MULTI_ANNOTATION_AMBIGUITY")

    if mode == DEFAULT_ELIGIBILITY:
        reasons.append("CONFIGURED_FULL_SHADOW")

    # Stable unique order
    seen = set()
    ordered: List[str] = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            ordered.append(r)
    return ordered


def should_invoke_claude(
    *,
    reasons: List[str],
    mode: str = DEFAULT_ELIGIBILITY,
) -> bool:
    """
    Future selective mode can require a non-full-shadow reason.
    This experiment always invokes when CONFIGURED_FULL_SHADOW is present.
    """
    if mode == DEFAULT_ELIGIBILITY:
        return True
    return any(r != "CONFIGURED_FULL_SHADOW" for r in reasons)


__all__ = ["eligibility_reasons", "should_invoke_claude"]
