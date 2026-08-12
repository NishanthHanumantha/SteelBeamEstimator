"""Structured response schema + parser for P2.5.3."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Tuple

from .config import (
    REINFORCEMENT_TYPES,
    SCHEMA_VERSION,
    STATUS_CONFLICT,
    STATUS_INSUFFICIENT,
    STATUS_PARTIAL,
    STATUS_RESOLVED,
)

MODEL_VERSION = "10.7.0"

ALLOWED_STATUSES = {
    STATUS_RESOLVED,
    STATUS_PARTIAL,
    STATUS_INSUFFICIENT,
    STATUS_CONFLICT,
}


def extract_json_object(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Parse JSON from Claude text; tolerate optional markdown fences."""
    if not text or not str(text).strip():
        return None, "empty_response"
    raw = str(text).strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        raw = fence.group(1)
    else:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start : end + 1]
    try:
        obj = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        return None, f"json_parse_error:{exc}"
    if not isinstance(obj, dict):
        return None, "json_not_object"
    return obj, None


def normalize_parsed(obj: Dict[str, Any]) -> Dict[str, Any]:
    spacing = obj.get("spacing_mm")
    if spacing is None:
        spacing = []
    if not isinstance(spacing, list):
        spacing = [spacing]
    visual = obj.get("visual_evidence")
    if visual is None:
        visual = []
    if not isinstance(visual, list):
        visual = [str(visual)]
    warnings = obj.get("warnings")
    if warnings is None:
        warnings = []
    if not isinstance(warnings, list):
        warnings = [str(warnings)]
    return {
        "candidate_id": obj.get("candidate_id"),
        "interpretation_status": obj.get("interpretation_status"),
        "reinforcement_type": obj.get("reinforcement_type"),
        "quantity": obj.get("quantity"),
        "diameter_mm": obj.get("diameter_mm"),
        "legs": obj.get("legs"),
        "spacing_mm": spacing,
        "spacing_pattern": obj.get("spacing_pattern"),
        "normalized_notation": obj.get("normalized_notation"),
        "confidence": obj.get("confidence"),
        "visual_evidence": visual,
        "reasoning_summary": obj.get("reasoning_summary") or "",
        "warnings": warnings,
        "schema_version": SCHEMA_VERSION,
    }


__all__ = [
    "ALLOWED_STATUSES",
    "REINFORCEMENT_TYPES",
    "extract_json_object",
    "normalize_parsed",
]
