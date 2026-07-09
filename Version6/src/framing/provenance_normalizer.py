"""Normalize provenance fields across engineering values."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.framing.engineering_status import (
    STATUS_DERIVED,
    STATUS_ESTIMATED,
    STATUS_KNOWN,
    STATUS_NOT_COMPUTED,
    STATUS_UNKNOWN,
    infer_status_from_dict,
)

GOVERNING_SOURCE = "ENGINEERING_LENGTH_MODEL"
CLEAR_SPAN_SOURCE = "SUPPORT_FACE"
EFFECTIVE_SPAN_SOURCE = "EFFECTIVE_SPAN_RESOLVER"
DESIGN_SPAN_SOURCE = "ENGINEERING_MODEL"


def normalize_engineering_value(
    data: dict[str, Any],
    field_hint: Optional[str] = None,
) -> dict[str, Any]:
    """Ensure status, source, confidence, and derived_from are populated."""
    if not data:
        return data

    result = dict(data)
    field = field_hint or ""

    if field == "governing_span":
        result.setdefault("source", GOVERNING_SOURCE)
        selected = str(result.get("selected_from", "")).upper()
        if selected == "CLEAR_SPAN":
            result["derived_from"] = result.get("derived_from") or ["CLEAR_SPAN", "SUPPORT_FACE"]
            result["status"] = STATUS_KNOWN
        elif selected == "EFFECTIVE_SPAN":
            result["derived_from"] = result.get("derived_from") or ["EFFECTIVE_SPAN"]
            result["status"] = STATUS_KNOWN
        elif selected == "CENTERLINE":
            result["derived_from"] = result.get("derived_from") or ["CENTERLINE"]
            result["status"] = STATUS_KNOWN
        else:
            result["derived_from"] = result.get("derived_from") or ["ENGINEERING_LENGTH_MODEL"]
            result["status"] = STATUS_DERIVED
        if not result.get("source"):
            result["source"] = GOVERNING_SOURCE

    elif field == "clear_span":
        result.setdefault("source", CLEAR_SPAN_SOURCE)
        result.setdefault("derived_from", ["SUPPORT_FACE"])
        if result.get("status") not in (STATUS_KNOWN, STATUS_ESTIMATED, STATUS_DERIVED):
            result["status"] = STATUS_KNOWN if result.get("value") is not None else STATUS_UNKNOWN

    elif field == "effective_span":
        result.setdefault("source", EFFECTIVE_SPAN_SOURCE)
        result.setdefault("derived_from", ["CLEAR_SPAN", "BEARING_LENGTH"])
        if result.get("status") not in (STATUS_KNOWN, STATUS_ESTIMATED, STATUS_DERIVED):
            result["status"] = infer_status_from_dict(result)

    elif field == "design_span":
        result.setdefault("source", DESIGN_SPAN_SOURCE)
        result.setdefault("derived_from", ["EFFECTIVE_SPAN"])
        if result.get("status") not in (STATUS_KNOWN, STATUS_ESTIMATED, STATUS_DERIVED):
            result["status"] = STATUS_ESTIMATED

    else:
        status = result.get("status")
        if status not in (STATUS_KNOWN, STATUS_ESTIMATED, STATUS_DERIVED, STATUS_UNKNOWN, STATUS_NOT_COMPUTED):
            result["status"] = infer_status_from_dict(result)

    status = result.get("status", STATUS_UNKNOWN)
    if status == STATUS_DERIVED and not result.get("source"):
        result["source"] = _infer_derived_source(field, result)
    if status == STATUS_DERIVED and not result.get("derived_from"):
        result["derived_from"] = _infer_derived_from(field, result)

    return result


def _infer_derived_source(field: str, data: dict[str, Any]) -> str:
    if field in ("governing_span", "clear_span", "effective_span", "design_span"):
        return GOVERNING_SOURCE
    if data.get("selected_from"):
        return GOVERNING_SOURCE
    return "ENGINEERING_MODEL"


def _infer_derived_from(field: str, data: dict[str, Any]) -> List[str]:
    selected = str(data.get("selected_from", "")).upper()
    if selected:
        deps = [selected]
        if selected == "CLEAR_SPAN":
            deps.append("SUPPORT_FACE")
        return deps
    if field == "governing_span":
        return ["CLEAR_SPAN", "SUPPORT_FACE"]
    return ["ENGINEERING_MODEL"]


def normalize_length_model(length_model: dict[str, Any]) -> dict[str, Any]:
    if not length_model:
        return length_model
    result = dict(length_model)
    field_map = {
        "centerline_length": "centerline_length",
        "support_face_length": "support_face_length",
        "bearing_length_left": "bearing_length_left",
        "bearing_length_right": "bearing_length_right",
        "clear_span": "clear_span",
        "effective_span": "effective_span",
        "design_span": "design_span",
        "governing_span": "governing_span",
    }
    for key, hint in field_map.items():
        if key in result and isinstance(result[key], dict):
            result[key] = normalize_engineering_value(result[key], hint)
    if not result.get("source"):
        result["source"] = "ENGINEERING_LENGTH_MODEL"
    return result


def normalize_status_registry_entry(entry: dict[str, Any]) -> dict[str, Any]:
    result = dict(entry)
    field = str(result.get("field", ""))
    payload = {
        "value": result.get("value"),
        "status": result.get("status"),
        "confidence": result.get("confidence", 0.0),
        "source": result.get("source", ""),
        "derived_from": result.get("derived_from"),
        "selected_from": result.get("selected_from"),
        "unit": result.get("unit"),
    }
    normalized = normalize_engineering_value(payload, field)
    result.update(normalized)
    return result


def normalize_beam_engineering_values(beam: dict[str, Any]) -> None:
    if beam.get("length_model"):
        beam["length_model"] = normalize_length_model(beam["length_model"])
    section = beam.get("beam_section", {})
    for key, val in list(section.items()):
        if isinstance(val, dict) and "value" in val:
            section[key] = normalize_engineering_value(val, key)
    dims = beam.get("dimensions", {}).get("section", {})
    for key, val in list(dims.items()):
        if isinstance(val, dict) and ("value" in val or "status" in val):
            dims[key] = normalize_engineering_value(val, key)
