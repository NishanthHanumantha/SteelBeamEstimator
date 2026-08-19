"""Observational evidence-conflict schema. Fail closed to SEMANTIC_UNUSABLE. Never a recovery decision."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from PhaseP253_claude_vision_interpretation_pilot.response_schema import extract_json_object

from .config import ALLOWED_CONFLICTS, SCHEMA_VERSION, SEM_UNUSABLE

ALLOWED_EQUIV = ("MATCH", "MISMATCH", "SAME", "DIFFERENT", "UNCERTAIN")


class ContractSchemaError(ValueError):
    """Invalid observational conflict-classification payload."""


def _as_confidence(value: Any) -> float:
    try:
        conf = float(value)
    except (TypeError, ValueError) as exc:
        raise ContractSchemaError(f"confidence not numeric: {value!r}") from exc
    if conf < 0.0 or conf > 1.0:
        raise ContractSchemaError(f"confidence out of bounds: {conf}")
    return conf


def _enum(value: Any, *, allowed: tuple, field: str) -> str:
    text = str(value or "").strip().upper()
    if text not in allowed:
        raise ContractSchemaError(f"invalid {field}: {text!r}")
    return text


def normalize_contract_payload(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise ContractSchemaError("payload is not an object")
    if "should_recover" in raw or "production_action" in raw or "quantity" in raw:
        raise ContractSchemaError("recovery/quantity fields are forbidden")
    spec = _enum(raw.get("specification_equivalence"), allowed=("MATCH", "MISMATCH", "UNCERTAIN"), field="specification_equivalence")
    target = _enum(raw.get("physical_target_equivalence"), allowed=("SAME", "DIFFERENT", "UNCERTAIN"), field="physical_target_equivalence")
    layer = _enum(raw.get("layer_equivalence"), allowed=("SAME", "DIFFERENT", "UNCERTAIN"), field="layer_equivalence")
    conflict = _enum(raw.get("conflict_type"), allowed=ALLOWED_CONFLICTS, field="conflict_type")
    rationale = raw.get("rationale")
    if rationale is not None and not isinstance(rationale, str):
        raise ContractSchemaError("rationale must be a string")
    return {
        "schema_version": SCHEMA_VERSION,
        "specification_equivalence": spec,
        "physical_target_equivalence": target,
        "layer_equivalence": layer,
        "conflict_type": conflict,
        "confidence": _as_confidence(raw.get("confidence")),
        "rationale": (rationale or "").strip(),
        "schema_ok": True,
        "usable": True,
    }


def parse_contract_response(raw_text: Optional[str]) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    report: Dict[str, Any] = {"ok": False, "error": None, "error_class": None, "usable": False}
    if not raw_text or not str(raw_text).strip():
        report["error"] = "empty_response"
        report["error_class"] = "empty_response"
        report["decision"] = SEM_UNUSABLE
        return None, report
    obj, err = extract_json_object(str(raw_text))
    if obj is None:
        report["error"] = err or "json_parse_error"
        report["error_class"] = "malformed_json"
        report["decision"] = SEM_UNUSABLE
        return None, report
    try:
        payload = normalize_contract_payload(obj)
    except ContractSchemaError as exc:
        report["error"] = str(exc)
        report["error_class"] = "schema_failure"
        report["decision"] = SEM_UNUSABLE
        return None, report
    report["ok"] = True
    report["usable"] = True
    return payload, report


def unusable(*, error_class: str, error: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "usable": False,
        "decision": SEM_UNUSABLE,
        "error_class": error_class,
        "error": error,
        "schema_ok": False,
    }


__all__ = [
    "ContractSchemaError",
    "normalize_contract_payload",
    "parse_contract_response",
    "unusable",
]
