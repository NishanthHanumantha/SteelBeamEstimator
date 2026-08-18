"""Strict P2.6.7 live semantic schema. Failed parses stay failed — never repaired from expected answers.

Supporting-field coercion (object/list → text) is schema tolerance only. Decision,
layer, representation, and confidence remain strict and are never filled in.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from PhaseP253_claude_vision_interpretation_pilot.response_schema import extract_json_object

from .config import (
    ALLOWED_DECISIONS,
    ALLOWED_LAYERS,
    ALLOWED_REPRESENTATION,
    LAYER_UNKNOWN,
    REP_UNCERTAIN,
    SCHEMA_VERSION,
)


class LiveSchemaError(ValueError):
    """Invalid structured live semantic payload."""


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "yes", "1"):
            return True
        if low in ("false", "no", "0"):
            return False
    raise LiveSchemaError(f"boolean field invalid: {value!r}")


def _as_confidence(value: Any) -> float:
    try:
        conf = float(value)
    except (TypeError, ValueError) as exc:
        raise LiveSchemaError(f"confidence not numeric: {value!r}") from exc
    if conf < 0.0 or conf > 1.0:
        raise LiveSchemaError(f"confidence out of bounds: {conf}")
    return conf


def _stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, ensure_ascii=True)
    return str(value).strip()


def _flatten_to_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, dict):
        items: List[str] = []
        for nested_key, nested_value in value.items():
            if isinstance(nested_value, list):
                for item in nested_value:
                    text = _stringify_value(item)
                    if text:
                        items.append(f"{nested_key}: {text}")
            else:
                text = _stringify_value(nested_value)
                if text:
                    items.append(f"{nested_key}: {text}")
        return items
    if isinstance(value, list):
        return [text for text in (_stringify_value(item) for item in value) if text]
    text = _stringify_value(value)
    return [text] if text else []


def _as_str_list(value: Any, *, field: str) -> List[str]:
    del field
    return _flatten_to_str_list(value)


def _as_notes(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = [_stringify_value(item) for item in value]
        return "; ".join(part for part in parts if part)
    return _stringify_value(value)


def _as_interpretation(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return _stringify_value(value)


def normalize_live_payload(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise LiveSchemaError("payload is not an object")
    decision = str(raw.get("decision") or "").strip().upper()
    if decision not in ALLOWED_DECISIONS:
        raise LiveSchemaError(f"invalid decision: {decision!r}")
    layer = str(raw.get("target_layer") or LAYER_UNKNOWN).strip().upper()
    if layer not in ALLOWED_LAYERS:
        raise LiveSchemaError(f"invalid target_layer: {layer!r}")
    assessment = str(raw.get("existing_representation_assessment") or REP_UNCERTAIN).strip().upper()
    if assessment not in ALLOWED_REPRESENTATION:
        raise LiveSchemaError(f"invalid existing_representation_assessment: {assessment!r}")
    interp = raw.get("annotation_interpretation")
    codes = raw.get("reason_codes")
    if codes is None:
        codes = raw.get("semantic_reason_codes")
    evidence = raw.get("evidence")
    if evidence is None:
        evidence = raw.get("visual_evidence")
    notes = raw.get("uncertainty_notes")
    coerced_fields: List[str] = []
    if isinstance(interp, (dict, list)):
        coerced_fields.append("annotation_interpretation")
    if isinstance(evidence, dict) or (isinstance(evidence, list) and any(isinstance(item, (dict, list)) for item in evidence)):
        coerced_fields.append("evidence")
    if isinstance(notes, (dict, list)):
        coerced_fields.append("uncertainty_notes")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "decision": decision,
        "confidence": _as_confidence(raw.get("confidence")),
        "target_layer": layer,
        "existing_representation_assessment": assessment,
        "deterministic_context_consistent": _as_bool(raw.get("deterministic_context_consistent"), False),
        "spatial_context_consistent": _as_bool(raw.get("spatial_context_consistent"), False),
        "conflict_present": _as_bool(raw.get("conflict_present"), False),
        "reason_codes": _as_str_list(codes, field="reason_codes"),
        "evidence": _as_str_list(evidence, field="evidence"),
        "annotation_interpretation": _as_interpretation(interp),
        "uncertainty_notes": _as_notes(notes),
        "schema_ok": True,
        "coerced_fields": coerced_fields,
    }
    return payload


def parse_live_response(raw_text: Optional[str]) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    report: Dict[str, Any] = {"ok": False, "error": None, "error_class": None}
    if not raw_text or not str(raw_text).strip():
        report["error"] = "empty_response"
        report["error_class"] = "empty_response"
        return None, report
    obj, err = extract_json_object(str(raw_text))
    if obj is None:
        report["error"] = err or "json_parse_error"
        report["error_class"] = "malformed_json"
        return None, report
    try:
        payload = normalize_live_payload(obj)
    except LiveSchemaError as exc:
        report["error"] = str(exc)
        report["error_class"] = "schema_failure"
        return None, report
    report["ok"] = True
    return payload, report


__all__ = [
    "LiveSchemaError",
    "normalize_live_payload",
    "parse_live_response",
]
