"""Hypothetical overlay only. Never written back as production routing."""
from __future__ import annotations

from typing import Any, Dict

from PhaseP265_spatial_context_longitudinal.config import STIRRUP_CALL_REASONS

from .config import (
    CONFIDENCE_SKIP_THRESHOLD,
    COVER_FULL,
    DECISION_CALL,
    DECISION_SKIP,
    REP_REPRESENTED,
    SEM_AMBIGUOUS,
    SEM_DISTINCT,
    SEM_DUPLICATE,
    SEM_UNSUPPORTED,
    SHADOW_AMBIGUOUS,
    SHADOW_DISTINCT,
    SHADOW_DUPLICATE,
    SHADOW_UNSUPPORTED,
)

_SHADOW = {
    SEM_DISTINCT: SHADOW_DISTINCT,
    SEM_DUPLICATE: SHADOW_DUPLICATE,
    SEM_AMBIGUOUS: SHADOW_AMBIGUOUS,
    SEM_UNSUPPORTED: SHADOW_UNSUPPORTED,
}


def is_safe_skip_candidate(semantic: Dict[str, Any]) -> bool:
    """High confidence alone is never sufficient."""
    if semantic.get("decision") != SEM_DUPLICATE:
        return False
    try:
        conf = float(semantic.get("confidence"))
    except (TypeError, ValueError):
        return False
    if conf < CONFIDENCE_SKIP_THRESHOLD:
        return False
    if semantic.get("existing_representation_assessment") != REP_REPRESENTED:
        return False
    if not semantic.get("deterministic_context_consistent"):
        return False
    if not semantic.get("spatial_context_consistent"):
        return False
    if semantic.get("conflict_present"):
        return False
    return True


def hypothetical_from_semantic(
    *,
    observed_decision: str,
    coverage: str,
    semantic: Dict[str, Any],
    reason_codes: Any = None,
) -> Dict[str, Any]:
    shadow = _SHADOW.get(str(semantic.get("decision") or ""), SHADOW_AMBIGUOUS)
    reasons = [str(r) for r in (reason_codes or [])]
    stirrup_call = any(r in STIRRUP_CALL_REASONS for r in reasons)
    if str(coverage or "") == COVER_FULL:
        return {
            "semantic_decision": shadow,
            "safe_skip_candidate": False,
            "hypothetical_vision_routing": (
                DECISION_SKIP if observed_decision == DECISION_SKIP else observed_decision
            ),
            "hypothetical_reason": "PRESERVE_FULLY_COVERED_PRODUCTION_PATH",
        }
    if observed_decision == DECISION_SKIP:
        return {
            "semantic_decision": shadow,
            "safe_skip_candidate": False,
            "hypothetical_vision_routing": DECISION_SKIP,
            "hypothetical_reason": "PRESERVE_OBSERVED_SKIP",
        }
    if stirrup_call:
        return {
            "semantic_decision": shadow,
            "safe_skip_candidate": False,
            "hypothetical_vision_routing": DECISION_CALL,
            "hypothetical_reason": "PRESERVE_STIRRUP_CALL",
        }
    if is_safe_skip_candidate(semantic):
        return {
            "semantic_decision": shadow,
            "safe_skip_candidate": True,
            "hypothetical_vision_routing": DECISION_SKIP,
            "hypothetical_reason": "SEMANTIC_DUPLICATE_MULTI_EVIDENCE_SKIP_CANDIDATE",
        }
    decision = str(semantic.get("decision") or "")
    if decision == SEM_DISTINCT:
        reason = "SEMANTIC_DISTINCT_CALL"
    elif decision in (SEM_AMBIGUOUS, SEM_UNSUPPORTED):
        reason = "SEMANTIC_CONSERVATIVE_CALL"
    elif decision == SEM_DUPLICATE:
        reason = "SEMANTIC_DUPLICATE_NOT_SAFE_TO_SKIP"
    else:
        reason = "SEMANTIC_CONSERVATIVE_CALL"
    return {
        "semantic_decision": shadow,
        "safe_skip_candidate": False,
        "hypothetical_vision_routing": DECISION_CALL,
        "hypothetical_reason": reason,
    }


__all__ = ["hypothetical_from_semantic", "is_safe_skip_candidate"]
