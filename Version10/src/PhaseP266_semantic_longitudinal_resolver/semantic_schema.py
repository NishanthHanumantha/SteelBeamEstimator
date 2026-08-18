"""Strict P2.6.6 semantic response schema. Free-form text is never a routing input."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PhaseP253_claude_vision_interpretation_pilot.response_schema import extract_json_object

from .config import (
    ALLOWED_DECISIONS,
    ALLOWED_LAYERS,
    ALLOWED_REASON_CODES,
    ALLOWED_REPRESENTATION,
    LAYER_UNKNOWN,
    REP_UNCERTAIN,
    SCHEMA_VERSION,
    SEM_AMBIGUOUS,
    SEM_UNSUPPORTED,
)


class SemanticSchemaError(ValueError):
    """Invalid structured semantic payload."""


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
    raise SemanticSchemaError(f"boolean field invalid: {value!r}")


def _as_confidence(value: Any) -> float:
    try:
        conf = float(value)
    except (TypeError, ValueError) as exc:
        raise SemanticSchemaError(f"confidence not numeric: {value!r}") from exc
    if conf < 0.0 or conf > 1.0:
        raise SemanticSchemaError(f"confidence out of bounds: {conf}")
    return conf


def _as_str_list(value: Any, *, field: str) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SemanticSchemaError(f"{field} must be a list")
    out: List[str] = []
    for item in value:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            out.append(text)
    return out


def _codes(value: Any) -> List[str]:
    codes = _as_str_list(value, field="semantic_reason_codes")
    bad = [c for c in codes if c not in ALLOWED_REASON_CODES]
    if bad:
        raise SemanticSchemaError(f"unknown semantic_reason_codes: {bad}")
    return codes


def empty_unsupported(*, reason: str, notes: Optional[str] = None) -> Dict[str, Any]:
    return {
        "decision": SEM_UNSUPPORTED,
        "confidence": 0.0,
        "annotation_interpretation": notes or "insufficient evidence",
        "target_layer": LAYER_UNKNOWN,
        "existing_representation_assessment": REP_UNCERTAIN,
        "semantic_reason_codes": [reason] if reason in ALLOWED_REASON_CODES else ["BEAM_CONTEXT_INSUFFICIENT"],
        "visual_evidence": [],
        "deterministic_context_consistent": False,
        "spatial_context_consistent": False,
        "conflict_present": False,
        "schema_version": SCHEMA_VERSION,
        "schema_ok": True,
    }


def normalize_semantic_payload(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise SemanticSchemaError("payload is not an object")
    decision = str(raw.get("decision") or "").strip().upper()
    if decision not in ALLOWED_DECISIONS:
        raise SemanticSchemaError(f"invalid decision: {decision!r}")
    layer = str(raw.get("target_layer") or LAYER_UNKNOWN).strip().upper()
    if layer not in ALLOWED_LAYERS:
        raise SemanticSchemaError(f"invalid target_layer: {layer!r}")
    assessment = str(raw.get("existing_representation_assessment") or REP_UNCERTAIN).strip().upper()
    if assessment not in ALLOWED_REPRESENTATION:
        raise SemanticSchemaError(f"invalid existing_representation_assessment: {assessment!r}")
    interp = raw.get("annotation_interpretation")
    if interp is not None and not isinstance(interp, str):
        raise SemanticSchemaError("annotation_interpretation must be a string")
    payload = {
        "decision": decision,
        "confidence": _as_confidence(raw.get("confidence")),
        "annotation_interpretation": (interp or "").strip(),
        "target_layer": layer,
        "existing_representation_assessment": assessment,
        "semantic_reason_codes": _codes(raw.get("semantic_reason_codes")),
        "visual_evidence": _as_str_list(raw.get("visual_evidence"), field="visual_evidence"),
        "deterministic_context_consistent": _as_bool(raw.get("deterministic_context_consistent"), True),
        "spatial_context_consistent": _as_bool(raw.get("spatial_context_consistent"), True),
        "conflict_present": _as_bool(raw.get("conflict_present"), False),
        "schema_version": SCHEMA_VERSION,
        "schema_ok": True,
    }
    return payload


def parse_semantic_response(raw_text: Optional[str]) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    report: Dict[str, Any] = {"ok": False, "error": None}
    if not raw_text or not str(raw_text).strip():
        report["error"] = "empty_response"
        return None, report
    obj, err = extract_json_object(str(raw_text))
    if obj is None:
        report["error"] = err or "json_parse_error"
        return None, report
    try:
        payload = normalize_semantic_payload(obj)
    except SemanticSchemaError as exc:
        report["error"] = str(exc)
        return None, report
    report["ok"] = True
    return payload, report


def validate_semantic_payload(raw: Any) -> Dict[str, Any]:
    return normalize_semantic_payload(raw)


__all__ = [
    "SemanticSchemaError",
    "empty_unsupported",
    "normalize_semantic_payload",
    "parse_semantic_response",
    "validate_semantic_payload",
]
