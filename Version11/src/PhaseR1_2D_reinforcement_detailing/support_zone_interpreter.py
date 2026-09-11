"""Support zone interpreter. MODEL_VERSION: 8.4.0"""
from __future__ import annotations

from typing import Any, Dict, List

MODEL_VERSION = "8.4.0"

LEFT_SUPPORT = "LEFT_SUPPORT"
RIGHT_SUPPORT = "RIGHT_SUPPORT"
MID_SPAN = "MID_SPAN"
BOTH_SUPPORTS = "BOTH_SUPPORTS"
FULL_SPAN = "FULL_SPAN"
UNKNOWN = "UNKNOWN"


class SupportZoneInterpreter:
    """Infer reinforcement support regions from intent + geometry evidence."""

    def interpret(self, intent: Any, span_mm: float = 0.0) -> Dict[str, Any]:
        evidence: List[str] = []
        extent = str(getattr(intent, "extent", "") or UNKNOWN)
        support = str(getattr(intent, "support_type", "") or UNKNOWN)
        role = str(getattr(intent, "role", "") or "")

        left = right = mid = False
        region = UNKNOWN
        conf = 0.5

        if extent in ("FULL_SPAN", "CONTINUOUS"):
            region, left, right, mid, conf = FULL_SPAN, True, True, True, 0.85
            evidence.append("extent_full_or_continuous")
        elif extent == "LEFT_SUPPORT":
            region, left, conf = LEFT_SUPPORT, True, 0.8
            evidence.append("extent_left_support")
        elif extent == "RIGHT_SUPPORT":
            region, right, conf = RIGHT_SUPPORT, True, 0.8
            evidence.append("extent_right_support")
        elif extent in ("SUPPORT_ZONE", "CURTAILED"):
            region, left, right, conf = BOTH_SUPPORTS, True, True, 0.75
            evidence.append("extent_support_zone_or_curtailed")
        elif extent in ("CENTRE_SPAN", "LOCAL_REINFORCEMENT"):
            region, mid, conf = MID_SPAN, True, 0.7
            evidence.append("extent_centre_or_local")
        elif role in ("TOP_MAIN", "BOTTOM_MAIN", "STIRRUP"):
            region, left, right, mid, conf = FULL_SPAN, True, True, True, 0.55
            evidence.append("role_suggests_full_span_low_conf")
        elif role in ("TOP_EXTRA", "BOTTOM_EXTRA"):
            region, left, right, conf = BOTH_SUPPORTS, True, True, 0.55
            evidence.append("extra_role_suggests_support_zones")
        else:
            region, conf = UNKNOWN, 0.35
            evidence.append("support_region_unknown")

        if support == "LEFT":
            left = True
            evidence.append("intent_support_type_left")
        elif support == "RIGHT":
            right = True
            evidence.append("intent_support_type_right")
        elif support == "BOTH":
            left = right = True
            evidence.append("intent_support_type_both")

        evidence.append(f"span_mm={span_mm}")
        return {
            "support_region": region,
            "left_support_zone": left,
            "mid_zone": mid,
            "right_support_zone": right,
            "confidence": conf,
            "evidence": evidence,
        }
