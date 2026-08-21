"""Validate Vision values before acceptance. Do not silently repair."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import (
    ALLOWED_LAYERS,
    ALLOWED_ROLES,
    ALLOWED_SCOPES,
    REASON_INCONSISTENT,
    REASON_LOW_CONF,
    REASON_SCHEMA,
    VISION_MIN_CONFIDENCE,
)
from .hybrid_authority_contract import authority_contract
from .normalize import diameter_supported, map_layer, parse_bar_count, parse_diameter


def _threshold() -> float:
    return float(authority_contract()["vision_min_confidence"] if authority_contract() else VISION_MIN_CONFIDENCE)


def confidence_ok(conf: Optional[float]) -> bool:
    if conf is None:
        return False
    return float(conf) >= _threshold()


def validate_field(
    *,
    field: str,
    vision_value: Any,
    confidence: Optional[float],
    spec: Any = None,
    bar_count: Any = None,
    diameter: Any = None,
    beam_usable: bool = True,
) -> Dict[str, Any]:
    if not beam_usable:
        return {"accepted": False, "reason": REASON_SCHEMA, "field": field}
    if not confidence_ok(confidence):
        return {"accepted": False, "reason": REASON_LOW_CONF, "field": field}
    if vision_value in (None, "", "UNKNOWN") and field not in ("SUPPORT_SCOPE", "ROLE"):
        if field == "ROLE" or field == "SUPPORT_SCOPE":
            pass
        else:
            return {"accepted": False, "reason": "VISION_MISSING_VALUE", "field": field}

    if field == "LAYER":
        layer = map_layer(vision_value)
        if layer not in ALLOWED_LAYERS and layer not in ("TOP", "BOTTOM", "STIRRUP", "SIDE_FACE", "OTHER", "UNKNOWN"):
            return {"accepted": False, "reason": "VISION_INVALID_LAYER", "field": field}
        if layer == "UNKNOWN" and str(vision_value or "").upper() not in ("UNKNOWN", ""):
            return {"accepted": False, "reason": "VISION_INVALID_LAYER", "field": field}
        return {"accepted": True, "reason": "VISION_ACCEPTED", "field": field, "normalized": layer}

    if field == "ROLE":
        role = str(vision_value or "UNKNOWN").upper()
        if role not in ALLOWED_ROLES:
            return {"accepted": False, "reason": "VISION_INVALID_ROLE", "field": field}
        if role == "UNKNOWN":
            return {"accepted": False, "reason": "VISION_MISSING_VALUE", "field": field}
        return {"accepted": True, "reason": "VISION_ACCEPTED", "field": field, "normalized": role}

    if field == "BAR_COUNT":
        try:
            n = int(vision_value)
        except (TypeError, ValueError):
            return {"accepted": False, "reason": "VISION_INVALID_BAR_COUNT", "field": field}
        if n <= 0:
            return {"accepted": False, "reason": "VISION_INVALID_BAR_COUNT", "field": field}
        implied = parse_bar_count(spec)
        if implied is not None and implied != n:
            return {"accepted": False, "reason": REASON_INCONSISTENT, "field": field}
        return {"accepted": True, "reason": "VISION_ACCEPTED", "field": field, "normalized": n}

    if field == "DIAMETER":
        try:
            d = int(vision_value)
        except (TypeError, ValueError):
            return {"accepted": False, "reason": "VISION_INVALID_DIAMETER", "field": field}
        if not diameter_supported(d):
            return {"accepted": False, "reason": "VISION_INVALID_DIAMETER", "field": field}
        implied = parse_diameter(spec)
        if implied is not None and implied != d:
            return {"accepted": False, "reason": REASON_INCONSISTENT, "field": field}
        return {"accepted": True, "reason": "VISION_ACCEPTED", "field": field, "normalized": d}

    if field == "SPECIFICATION":
        if vision_value in (None, ""):
            return {"accepted": False, "reason": "VISION_MISSING_VALUE", "field": field}
        implied_c = parse_bar_count(vision_value)
        implied_d = parse_diameter(vision_value)
        if bar_count not in (None, "", "UNKNOWN") and implied_c is not None:
            try:
                if int(bar_count) != implied_c:
                    return {"accepted": False, "reason": REASON_INCONSISTENT, "field": field}
            except (TypeError, ValueError):
                return {"accepted": False, "reason": REASON_INCONSISTENT, "field": field}
        if diameter not in (None, "", "UNKNOWN") and implied_d is not None:
            try:
                if int(diameter) != implied_d:
                    return {"accepted": False, "reason": REASON_INCONSISTENT, "field": field}
            except (TypeError, ValueError):
                return {"accepted": False, "reason": REASON_INCONSISTENT, "field": field}
        return {"accepted": True, "reason": "VISION_ACCEPTED", "field": field, "normalized": vision_value}

    if field == "SUPPORT_SCOPE":
        scope = str(vision_value or "UNKNOWN").upper()
        if scope not in ALLOWED_SCOPES:
            return {"accepted": False, "reason": "VISION_INVALID_SCOPE", "field": field}
        if scope == "UNKNOWN":
            return {"accepted": False, "reason": "VISION_MISSING_VALUE", "field": field}
        return {"accepted": True, "reason": "VISION_ACCEPTED", "field": field, "normalized": scope}

    if field == "TARGET_IDENTITY":
        if vision_value in (None, "", False):
            return {"accepted": False, "reason": "VISION_TARGET_NOT_IDENTIFIED", "field": field}
        return {"accepted": True, "reason": "VISION_ACCEPTED", "field": field, "normalized": vision_value}

    if vision_value in (None, ""):
        return {"accepted": False, "reason": "VISION_MISSING_VALUE", "field": field}
    return {"accepted": True, "reason": "VISION_ACCEPTED", "field": field, "normalized": vision_value}


def flag_possible_duplicates(groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flags = []
    keys: Dict[tuple, List[str]] = {}
    for g in groups:
        key = (
            str(g.get("layer")),
            str(g.get("role")),
            str(g.get("specification") or ""),
            str(g.get("bar_count")),
            str(g.get("diameter")),
        )
        keys.setdefault(key, []).append(str(g.get("physical_group_id")))
    for key, ids in keys.items():
        if len(ids) > 1:
            flags.append({"code": "POSSIBLE_DUPLICATE_GROUP", "group_ids": ids, "key": list(key)})
    return flags


__all__ = ["confidence_ok", "flag_possible_duplicates", "validate_field"]
