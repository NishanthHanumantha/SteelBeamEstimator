"""Hypothetical overlay only. Never written back as production routing."""
from __future__ import annotations

from typing import Any, Dict, List

from .config import (
    COVER_LAYER,
    DECISION_CALL,
    DECISION_SKIP,
    STATUS_SKIP,
    STIRRUP_CALL_REASONS,
)


def hypothetical_decision(observed: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(observed)
    reasons = [str(r) for r in (observed.get("reason_codes") or [])]
    stirrup = any(r in STIRRUP_CALL_REASONS for r in reasons)
    can_skip = (
        observed.get("decision") == DECISION_CALL
        and observed.get("context_status") == STATUS_SKIP
        and observed.get("longitudinal_coverage") == COVER_LAYER
        and not stirrup
    )
    if can_skip:
        out["hypothetical_decision"] = DECISION_SKIP
        out["hypothetical_reason"] = "CONTEXT_SUPPORTS_SKIP_NO_STIRRUP_GAP"
        out["decision"] = DECISION_SKIP
    else:
        out["hypothetical_decision"] = observed.get("decision")
        out["hypothetical_reason"] = "PRESERVE_OBSERVED_P264"
    return out


def apply_hypothetical(decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [hypothetical_decision(d) for d in decisions]


__all__ = ["apply_hypothetical", "hypothetical_decision"]
