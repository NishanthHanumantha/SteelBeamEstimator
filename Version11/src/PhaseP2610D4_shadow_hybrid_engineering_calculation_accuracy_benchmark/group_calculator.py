"""Shadow group engineering calculation. Vision semantics + deterministic cut/weight engines."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from .config import STATUS_CALCULATED, STATUS_GROUP_AMBIGUOUS, STATUS_INCOMPATIBLE, STATUS_PARTIAL, STATUS_WITHHELD
from .engineering_adapter import derive_cut_length_mm, map_engineering_role, numeric_cut, weight_kg


def _sem(group: Dict[str, Any]) -> Dict[str, Any]:
    raw = group.get("semantic") if isinstance(group.get("semantic"), dict) else {}
    out = dict(raw)
    recs = raw.get("field_records") if isinstance(raw.get("field_records"), dict) else {}
    for key in ("layer", "role", "bar_count", "diameter", "specification", "support_scope"):
        val = out.get(key)
        if isinstance(val, dict):
            out[key] = val.get("value")
        elif out.get(key) is None and isinstance(recs.get(key), dict):
            out[key] = recs[key].get("value")
    return out


def calculate_group(group: Dict[str, Any], *, geometry: Dict[str, Any]) -> Dict[str, Any]:
    sem = _sem(group)
    bind = group.get("engineering_binding") if isinstance(group.get("engineering_binding"), dict) else {}
    origin = str(group.get("origin") or "")
    ambiguous = bool(group.get("ambiguous")) or str(bind.get("binding_status") or "") == "AMBIGUOUS"
    out = {
        "beam_id": group.get("beam_id"),
        "group_id": group.get("group_id"),
        "origin": origin,
        "ambiguous": ambiguous,
        "possible_duplicate": bool(group.get("possible_duplicate")),
        "semantic": deepcopy(sem),
        "diameter_mm": sem.get("diameter"),
        "bar_count": sem.get("bar_count"),
        "layer": sem.get("layer"),
        "role": sem.get("role"),
        "support_scope": sem.get("support_scope"),
        "cut_length_mm": None,
        "cut_length_source": None,
        "quantity": sem.get("bar_count"),
        "weight_kg": None,
        "status": STATUS_CALCULATED,
        "reasons": [],
        "fallback_used": False,
    }
    if ambiguous:
        out["status"] = STATUS_GROUP_AMBIGUOUS
        out["reasons"] = [STATUS_WITHHELD]
        return out
    if str(bind.get("binding_status") or "") in ("INVALID_INPUT", "UNSUPPORTED", "MISSING_GEOMETRY"):
        out["status"] = STATUS_INCOMPATIBLE
        out["reasons"] = [str(bind.get("binding_status"))]
        return out
    dia = sem.get("diameter")
    qty = sem.get("bar_count")
    try:
        dia_f = float(dia) if dia is not None else None
        qty_i = int(qty) if qty is not None else None
    except (TypeError, ValueError):
        dia_f, qty_i = None, None
    if dia_f is None or qty_i is None or dia_f <= 0 or qty_i <= 0:
        out["status"] = STATUS_PARTIAL
        out["reasons"] = ["INVALID_SEMANTIC_INPUT"]
        return out
    eng_role = map_engineering_role(sem.get("layer"), sem.get("role"))
    provided = numeric_cut(bind.get("instance_cut_length_reference"))
    span = None
    geo_ref = bind.get("beam_geometry_reference") if isinstance(bind.get("beam_geometry_reference"), dict) else {}
    span_ref = bind.get("span_reference") if isinstance(bind.get("span_reference"), dict) else {}
    span = span_ref.get("span_mm") or geo_ref.get("span_mm") or geometry.get("span_mm")
    width = None
    depth = None
    sec = bind.get("section_geometry_reference") if isinstance(bind.get("section_geometry_reference"), dict) else {}
    width = sec.get("width_mm") or geometry.get("width_mm")
    depth = sec.get("depth_mm") or geometry.get("depth_mm")
    cut, cut_src = derive_cut_length_mm(
        role=eng_role,
        diameter_mm=dia_f,
        span_mm=float(span or 0.0),
        depth_mm=float(depth) if depth is not None else None,
        width_mm=float(width) if width is not None else None,
        provided_cut_mm=provided,
    )
    if provided is None:
        out["fallback_used"] = True
        out["reasons"].append("CUT_LENGTH_DERIVED_FROM_DETERMINISTIC_ENGINE")
        if origin == "VISION_ONLY_GROUP":
            out["reasons"].append("VISION_ONLY_NO_INSTANCE_CUT")
    else:
        out["reasons"].append("EXISTING_DETERMINISTIC_CUT_LENGTH")
    if cut is None:
        out["status"] = STATUS_PARTIAL
        out["reasons"].append("CUT_LENGTH_UNAVAILABLE")
        return out
    w = weight_kg(dia_f, cut, qty_i)
    out["cut_length_mm"] = cut
    out["cut_length_source"] = cut_src
    out["quantity"] = qty_i
    out["diameter_mm"] = dia_f
    out["engineering_role"] = eng_role
    out["weight_kg"] = w
    out["status"] = STATUS_CALCULATED
    recs = sem.get("field_records") if isinstance(sem.get("field_records"), dict) else {}
    for field in ("diameter", "role", "bar_count", "layer"):
        rec = recs.get(field) if isinstance(recs.get(field), dict) else {}
        if rec.get("source") == "VISION" and rec.get("fallback_used"):
            out["reasons"].append(f"EXPLICIT_FALLBACK_{field.upper()}")
    return out


__all__ = ["calculate_group"]
