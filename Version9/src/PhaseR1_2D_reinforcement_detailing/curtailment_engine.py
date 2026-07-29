"""Curtailment engine. MODEL_VERSION: 8.4.0"""
from __future__ import annotations

from typing import Any, Dict, List

MODEL_VERSION = "8.4.0"

LEFT_SUPPORT = "LEFT_SUPPORT"
RIGHT_SUPPORT = "RIGHT_SUPPORT"
MID_SPAN = "MID_SPAN"
BOTH_SUPPORTS = "BOTH_SUPPORTS"
FULL_SPAN = "FULL_SPAN"
CURTAILED = "CURTAILED"
UNKNOWN = "UNKNOWN"


class CurtailmentEngine:
    """Resolve curtailment type — do not fabricate offset lengths."""

    def interpret(self, intent: Any, support: Dict[str, Any]) -> Dict[str, Any]:
        evidence: List[str] = []
        extent = str(getattr(intent, "extent", "") or UNKNOWN)
        region = support.get("support_region") or UNKNOWN
        role = str(getattr(intent, "role", "") or "")

        mapping = {
            "FULL_SPAN": FULL_SPAN,
            "CONTINUOUS": FULL_SPAN,
            "LEFT_SUPPORT": LEFT_SUPPORT,
            "RIGHT_SUPPORT": RIGHT_SUPPORT,
            "SUPPORT_ZONE": BOTH_SUPPORTS,
            "CURTAILED": CURTAILED,
            "CENTRE_SPAN": MID_SPAN,
            "LOCAL_REINFORCEMENT": MID_SPAN,
        }
        ctype = mapping.get(extent)
        conf = 0.7 if ctype else 0.4
        if ctype:
            evidence.append(f"extent_map={extent}->{ctype}")
        else:
            ctype = region if region != UNKNOWN else UNKNOWN
            evidence.append(f"fallback_support_region={region}")
            conf = 0.45

        if role in ("TOP_MAIN", "BOTTOM_MAIN") and ctype in (LEFT_SUPPORT, RIGHT_SUPPORT):
            evidence.append("main_with_single_support_curtailment_flag")

        start_off = end_off = None
        if ctype == FULL_SPAN:
            start_off = end_off = 0.0
        elif ctype in (BOTH_SUPPORTS, CURTAILED):
            evidence.append("offsets_not_fabricated")

        return {
            "curtailment_type": ctype or UNKNOWN,
            "start_offset_mm": start_off,
            "end_offset_mm": end_off,
            "confidence": conf,
            "evidence": evidence,
        }
