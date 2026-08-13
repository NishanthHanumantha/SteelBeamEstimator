"""Structured semantic response schema + parser for P2.5.4."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from PhaseP253_claude_vision_interpretation_pilot.response_schema import (
    extract_json_object,
)

from .config import (
    BEAM_ASSOCIATIONS,
    ROLES,
    SCHEMA_VERSION,
    SEMANTIC_TYPES,
    STATUS_CONFLICT,
    STATUS_INSUFFICIENT,
    STATUS_PARTIAL,
    STATUS_RESOLVED,
)

MODEL_VERSION = "10.8.0"

ALLOWED_STATUSES = {
    STATUS_RESOLVED,
    STATUS_PARTIAL,
    STATUS_INSUFFICIENT,
    STATUS_CONFLICT,
}


def normalize_parsed(obj: Dict[str, Any]) -> Dict[str, Any]:
    spacing = obj.get("spacing_mm")
    if spacing is None:
        spacing = []
    if not isinstance(spacing, list):
        spacing = [spacing]
    evidence = obj.get("evidence_basis") or obj.get("visual_evidence")
    if evidence is None:
        evidence = []
    if not isinstance(evidence, list):
        evidence = [str(evidence)]
    warnings = obj.get("warnings")
    if warnings is None:
        warnings = []
    if not isinstance(warnings, list):
        warnings = [str(warnings)]
    # Accept P2.5.3-style reinforcement_type as semantic_type alias
    semantic_type = obj.get("semantic_type") or obj.get("reinforcement_type")
    if semantic_type == "SIDE_FACE":
        semantic_type = "SIDE_FACE_REINFORCEMENT"
    return {
        "candidate_id": obj.get("candidate_id"),
        "interpretation_status": obj.get("interpretation_status"),
        "semantic_type": semantic_type,
        "role": obj.get("role") or "UNKNOWN",
        "quantity": obj.get("quantity"),
        "diameter_mm": obj.get("diameter_mm"),
        "legs": obj.get("legs"),
        "spacing_mm": spacing,
        "spacing_pattern": obj.get("spacing_pattern"),
        "beam_association": obj.get("beam_association") or "UNCERTAIN",
        "zone": obj.get("zone") or "UNKNOWN",
        "normalized_notation": obj.get("normalized_notation"),
        "confidence": obj.get("confidence"),
        "evidence_basis": evidence,
        "warnings": warnings,
        "schema_version": SCHEMA_VERSION,
    }


__all__ = [
    "ALLOWED_STATUSES",
    "BEAM_ASSOCIATIONS",
    "ROLES",
    "SEMANTIC_TYPES",
    "extract_json_object",
    "normalize_parsed",
]
