"""Bind hybrid support scope to existing deterministic support / span references. No new support logic."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .config import SUPPORT_SCOPES_NEEDING_SUPPORT

_SCOPE_ALIASES = {
    "FULL_SPAN": "FULL_SPAN",
    "FULL": "FULL_SPAN",
    "LEFT_SUPPORT": "LEFT_SUPPORT",
    "LEFT": "LEFT_SUPPORT",
    "PARTIAL_LEFT": "LEFT_SUPPORT",
    "RIGHT_SUPPORT": "RIGHT_SUPPORT",
    "RIGHT": "RIGHT_SUPPORT",
    "PARTIAL_RIGHT": "RIGHT_SUPPORT",
    "BOTH_SUPPORTS": "BOTH_SUPPORTS",
    "BOTH": "BOTH_SUPPORTS",
    "PARTIAL_SUPPORT": "BOTH_SUPPORTS",
    "INTERMEDIATE_SUPPORT": "INTERMEDIATE_SUPPORT",
    "INTERMEDIATE": "INTERMEDIATE_SUPPORT",
    "MIDSPAN": "INTERMEDIATE_SUPPORT",
}


def normalize_scope(raw: Any) -> str:
    if raw is None or raw == "":
        return "UNKNOWN"
    token = str(raw).strip().upper().replace("-", "_").replace(" ", "_")
    return _SCOPE_ALIASES.get(token, token if token else "UNKNOWN")


def _zone_type(zone: Dict[str, Any]) -> str:
    raw = zone.get("support_type") or zone.get("type") or zone.get("side") or zone.get("location") or ""
    return normalize_scope(raw)


def _filter_zones(zones: List[Dict[str, Any]], wanted: str) -> List[Dict[str, Any]]:
    hits = []
    for z in zones:
        if not isinstance(z, dict):
            continue
        zt = _zone_type(z)
        if wanted == "BOTH_SUPPORTS" and zt in ("LEFT_SUPPORT", "RIGHT_SUPPORT", "BOTH_SUPPORTS"):
            hits.append(z)
        elif zt == wanted:
            hits.append(z)
    return hits


def _ref(zone: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": "DETERMINISTIC",
        "kind": "EXISTING_SUPPORT_ZONE",
        "support_id": zone.get("support_id") or zone.get("id"),
        "support_type": _zone_type(zone),
        "position_fraction": zone.get("position_fraction"),
    }


def bind_support(
    *,
    support_scope: Any,
    model: Optional[Dict[str, Any]],
    span_mm: Optional[float],
) -> Dict[str, Any]:
    scope = normalize_scope(support_scope)
    zones_raw = (model or {}).get("support_zones") if isinstance(model, dict) else None
    zones = [z for z in (zones_raw or []) if isinstance(z, dict)]
    required = scope in SUPPORT_SCOPES_NEEDING_SUPPORT
    span_ref = None
    if scope == "FULL_SPAN" and span_mm is not None:
        span_ref = {
            "source": "DETERMINISTIC",
            "kind": "FULL_SPAN",
            "span_mm": span_mm,
        }
        return {
            "scope": scope,
            "required": False,
            "span_reference": span_ref,
            "support_reference": {"source": "DETERMINISTIC", "kind": "NOT_REQUIRED", "reason": "FULL_SPAN"},
            "ambiguous": False,
            "missing": False,
            "reason": "SPAN_BOUND_FULL_SPAN",
        }
    if scope in ("UNKNOWN", "") and span_mm is not None:
        span_ref = {
            "source": "DETERMINISTIC",
            "kind": "GEOMETRIC_SPAN_AVAILABLE",
            "span_mm": span_mm,
        }
        return {
            "scope": scope,
            "required": False,
            "span_reference": span_ref,
            "support_reference": {"source": "DETERMINISTIC", "kind": "NOT_REQUIRED", "reason": "SCOPE_UNKNOWN"},
            "ambiguous": False,
            "missing": False,
            "partial": True,
            "reason": "SCOPE_UNKNOWN_SPAN_AVAILABLE",
        }
    if not required:
        if span_mm is not None:
            span_ref = {"source": "DETERMINISTIC", "kind": "GEOMETRIC_SPAN_AVAILABLE", "span_mm": span_mm}
        return {
            "scope": scope,
            "required": False,
            "span_reference": span_ref,
            "support_reference": {"source": "DETERMINISTIC", "kind": "NOT_REQUIRED", "reason": "SUPPORT_NOT_REQUIRED"},
            "ambiguous": False,
            "missing": False,
            "reason": "SUPPORT_NOT_REQUIRED",
        }
    if not zones:
        return {
            "scope": scope,
            "required": True,
            "span_reference": {"source": "DETERMINISTIC", "kind": "GEOMETRIC_SPAN_AVAILABLE", "span_mm": span_mm} if span_mm is not None else None,
            "support_reference": None,
            "ambiguous": False,
            "missing": True,
            "reason": "MISSING_SUPPORT_REFERENCE",
        }
    hits = _filter_zones(zones, scope)
    if scope == "BOTH_SUPPORTS":
        left = _filter_zones(zones, "LEFT_SUPPORT")
        right = _filter_zones(zones, "RIGHT_SUPPORT")
        both = _filter_zones(zones, "BOTH_SUPPORTS")
        if len(left) == 1 and len(right) == 1:
            return {
                "scope": scope,
                "required": True,
                "span_reference": {"source": "DETERMINISTIC", "kind": "BOTH_SUPPORTS", "span_mm": span_mm},
                "support_reference": {"source": "DETERMINISTIC", "kind": "BOTH_SUPPORTS", "zones": [_ref(left[0]), _ref(right[0])]},
                "ambiguous": False,
                "missing": False,
                "reason": "SUPPORT_BOUND_BOTH",
            }
        if len(both) == 1:
            return {
                "scope": scope,
                "required": True,
                "span_reference": {"source": "DETERMINISTIC", "kind": "BOTH_SUPPORTS", "span_mm": span_mm},
                "support_reference": _ref(both[0]),
                "ambiguous": False,
                "missing": False,
                "reason": "SUPPORT_BOUND_BOTH",
            }
        if hits:
            return {
                "scope": scope,
                "required": True,
                "span_reference": {"source": "DETERMINISTIC", "kind": "BOTH_SUPPORTS", "span_mm": span_mm},
                "support_reference": None,
                "ambiguous": True,
                "missing": False,
                "reason": "AMBIGUOUS_SUPPORT_REFERENCE",
            }
        return {
            "scope": scope,
            "required": True,
            "span_reference": {"source": "DETERMINISTIC", "kind": "GEOMETRIC_SPAN_AVAILABLE", "span_mm": span_mm} if span_mm is not None else None,
            "support_reference": None,
            "ambiguous": False,
            "missing": True,
            "reason": "MISSING_SUPPORT_REFERENCE",
        }
    if len(hits) == 1:
        return {
            "scope": scope,
            "required": True,
            "span_reference": {"source": "DETERMINISTIC", "kind": scope, "span_mm": span_mm},
            "support_reference": _ref(hits[0]),
            "ambiguous": False,
            "missing": False,
            "reason": "SUPPORT_BOUND",
        }
    if len(hits) > 1:
        return {
            "scope": scope,
            "required": True,
            "span_reference": {"source": "DETERMINISTIC", "kind": scope, "span_mm": span_mm},
            "support_reference": None,
            "ambiguous": True,
            "missing": False,
            "reason": "AMBIGUOUS_SUPPORT_REFERENCE",
        }
    if len(zones) == 1 and scope in ("LEFT_SUPPORT", "RIGHT_SUPPORT", "INTERMEDIATE_SUPPORT"):
        return {
            "scope": scope,
            "required": True,
            "span_reference": {"source": "DETERMINISTIC", "kind": scope, "span_mm": span_mm},
            "support_reference": None,
            "ambiguous": True,
            "missing": False,
            "reason": "AMBIGUOUS_SUPPORT_REFERENCE",
        }
    return {
        "scope": scope,
        "required": True,
        "span_reference": {"source": "DETERMINISTIC", "kind": "GEOMETRIC_SPAN_AVAILABLE", "span_mm": span_mm} if span_mm is not None else None,
        "support_reference": None,
        "ambiguous": False,
        "missing": True,
        "reason": "MISSING_SUPPORT_REFERENCE",
    }


def shuffle_safe_key(zones: List[Dict[str, Any]]) -> Tuple:
    """Canonical identity independent of input order."""
    keys = []
    for z in zones:
        if isinstance(z, dict):
            keys.append((str(z.get("support_id") or ""), _zone_type(z)))
    return tuple(sorted(keys))


__all__ = ["bind_support", "normalize_scope", "shuffle_safe_key"]
