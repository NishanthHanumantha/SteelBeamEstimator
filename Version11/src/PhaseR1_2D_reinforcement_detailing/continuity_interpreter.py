"""Continuity interpreter. MODEL_VERSION: 8.4.0"""
from __future__ import annotations

from typing import Any, Dict, List

MODEL_VERSION = "8.4.0"

CONTINUOUS = "CONTINUOUS"
CURTAILED = "CURTAILED"
SINGLE_SPAN = "SINGLE_SPAN"
LAPPED = "LAPPED"
TERMINATED = "TERMINATED"
UNKNOWN = "UNKNOWN"
FULL_SPAN = "FULL_SPAN"


class ContinuityInterpreter:
    """Determine continuity without silent defaults."""

    def interpret(self, intent: Any, support: Dict[str, Any]) -> Dict[str, Any]:
        evidence: List[str] = []
        cont = str(getattr(intent, "continuity", "") or "")
        extent = str(getattr(intent, "extent", "") or "")
        role = str(getattr(intent, "role", "") or "")
        conf = 0.5
        result = UNKNOWN

        known = {CONTINUOUS, CURTAILED, SINGLE_SPAN, LAPPED, TERMINATED}
        if cont in known:
            result, conf = cont, 0.8
            evidence.append(f"intent_continuity={cont}")
        elif extent in ("FULL_SPAN", "CONTINUOUS"):
            result = CONTINUOUS if role in ("TOP_MAIN", "BOTTOM_MAIN") else SINGLE_SPAN
            conf = 0.72
            evidence.append("extent_implies_continuity")
        elif extent in ("SUPPORT_ZONE", "CURTAILED", "LEFT_SUPPORT", "RIGHT_SUPPORT"):
            result, conf = CURTAILED, 0.75
            evidence.append("extent_implies_curtailed")
        elif support.get("support_region") == FULL_SPAN:
            result = CONTINUOUS if "MAIN" in role else SINGLE_SPAN
            conf = 0.6
            evidence.append("support_full_span_continuity")
        else:
            result, conf = UNKNOWN, 0.35
            evidence.append("continuity_unresolved_flagged")

        return {"continuity": result, "confidence": conf, "evidence": evidence}
