"""Bind hybrid groups to existing deterministic geometry. No new dimensions. No beam-ID branches."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .config import STATUS_MISSING_GEOM

_DIR_MAP = {
    "HORIZONTAL": "HORIZONTAL",
    "H": "HORIZONTAL",
    "X": "HORIZONTAL",
    "VERTICAL": "VERTICAL",
    "V": "VERTICAL",
    "Y": "VERTICAL",
}


def _num(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_direction(raw: Any) -> str:
    if raw is None or raw == "":
        return "UNKNOWN"
    token = str(raw).strip().upper()
    if token in _DIR_MAP:
        return _DIR_MAP[token]
    if token in ("HORIZONTAL", "VERTICAL", "OTHER", "UNKNOWN"):
        return token
    if token in ("FRAMING_PLAN_LINE", "PLAN"):
        return "UNKNOWN"
    return "OTHER" if token else "UNKNOWN"


def extract_geometry(model: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(model, dict) or not model:
        return {
            "available": False,
            "reason": STATUS_MISSING_GEOM,
            "beam_geometry_reference": None,
            "section_geometry_reference": None,
            "width_mm": None,
            "depth_mm": None,
            "span_mm": None,
            "clear_span_mm": None,
            "longitudinal_direction": "UNKNOWN",
            "geometry_source": None,
        }
    geo = model.get("geometry") if isinstance(model.get("geometry"), dict) else {}
    width = _num(geo.get("width_mm"))
    depth = _num(geo.get("depth_mm"))
    span = _num(geo.get("effective_span_mm"))
    clear = _num(geo.get("clear_span_mm"))
    if span is None:
        span = clear
    direction = normalize_direction(geo.get("orientation") or geo.get("direction") or geo.get("axis"))
    section_ok = width is not None and depth is not None
    available = section_ok or span is not None
    section_ref = None
    if section_ok:
        section_ref = {
            "source": "DETERMINISTIC",
            "width_mm": width,
            "depth_mm": depth,
            "kind": "EXISTING_SECTION_GEOMETRY",
        }
    beam_ref = None
    if available:
        beam_ref = {
            "source": "DETERMINISTIC",
            "kind": "EXISTING_BEAM_GEOMETRY",
            "geometry_source": geo.get("geometry_source"),
            "span_mm": span,
            "clear_span_mm": clear,
        }
    return {
        "available": bool(available),
        "section_available": bool(section_ok),
        "reason": None if available else STATUS_MISSING_GEOM,
        "beam_geometry_reference": beam_ref,
        "section_geometry_reference": section_ref,
        "width_mm": width,
        "depth_mm": depth,
        "span_mm": span,
        "clear_span_mm": clear,
        "longitudinal_direction": direction,
        "geometry_source": geo.get("geometry_source"),
    }


def bind_geometry(*, beam_id: str, catalog: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve geometry for the same discovered beam only. No cross-beam matching."""
    model = None
    if isinstance(catalog, dict):
        model = catalog.get(beam_id)
    return extract_geometry(model)


__all__ = ["bind_geometry", "extract_geometry", "normalize_direction"]
