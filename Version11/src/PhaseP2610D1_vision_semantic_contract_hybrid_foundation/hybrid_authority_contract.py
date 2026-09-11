"""Machine-readable hybrid field-authority contract. No beam-ID logic."""
from __future__ import annotations

from typing import Any, Dict, List

from .config import (
    AUTH_DET,
    AUTH_DET_ENG,
    AUTH_PRODUCTION,
    AUTH_VISION,
    CONTRACT_VERSION,
    VISION_MIN_CONFIDENCE,
)

VISION_PREFERRED_FIELDS = (
    "TARGET_IDENTITY",
    "LAYER",
    "PHYSICAL_GROUP_DETECTION",
    "BAR_COUNT",
    "DIAMETER",
    "SPECIFICATION",
    "ROLE",
    "SUPPORT_SCOPE",
    "STIRRUP_IDENTIFICATION",
)

DETERMINISTIC_AUTHORITY_FIELDS = (
    "SPACER",
    "GEOMETRY",
    "CUT_LENGTH",
    "DEVELOPMENT_LENGTH",
    "ANCHORAGE",
    "HOOKS_BENDS",
    "STIRRUP_ENGINEERING_CALCULATION",
    "PIECE_GENERATION",
    "WEIGHT",
    "BBS",
    "WORKBOOK",
)


def _vision(field: str, notes: str) -> Dict[str, Any]:
    return {
        "field_name": field,
        "authority": AUTH_VISION,
        "fallback_authority": AUTH_DET,
        "validation_required": True,
        "confidence_threshold": VISION_MIN_CONFIDENCE,
        "notes": notes,
    }


def _det(field: str, notes: str, *, engineering: bool = True) -> Dict[str, Any]:
    return {
        "field_name": field,
        "authority": AUTH_DET_ENG if engineering else AUTH_PRODUCTION,
        "fallback_authority": AUTH_DET,
        "validation_required": False,
        "confidence_threshold": None,
        "notes": notes,
    }


def authority_contract() -> Dict[str, Any]:
    fields: List[Dict[str, Any]] = [
        _vision("TARGET_IDENTITY", "Vision preferred for target association. Deterministic identity remains available."),
        _vision("LAYER", "Vision preferred for TOP/BOTTOM/STIRRUP/SIDE visual layer."),
        _vision("PHYSICAL_GROUP_DETECTION", "Distinct physical groups must not merge on identical spec or count."),
        _vision("BAR_COUNT", "Vision preferred for visible bar-count notation."),
        _vision("DIAMETER", "Vision preferred. Deterministic diameter is fallback and diagnostic only."),
        _vision("SPECIFICATION", "Vision preferred. Normalize without destroying count/diameter/legs/spacing."),
        _vision("ROLE", "MAIN/EXTRA is Vision preferred. Deterministic role is fallback only."),
        _vision("SUPPORT_SCOPE", "Semantic evidence only. Do not force engineering calculations in D.1."),
        _vision("STIRRUP_IDENTIFICATION", "Vision owns visual stirrup identification. Quantity calculation remains deterministic."),
        _det("SPACER", "Spacers are engineering-derived. Vision is not responsible."),
        _det("GEOMETRY", "Beam width/depth/span/support geometry remain deterministic."),
        _det("CUT_LENGTH", "Vision must never own cut length."),
        _det("DEVELOPMENT_LENGTH", "Engineering calculation remains deterministic."),
        _det("ANCHORAGE", "Engineering calculation remains deterministic."),
        _det("HOOKS_BENDS", "Engineering calculation remains deterministic."),
        _det("STIRRUP_ENGINEERING_CALCULATION", "Zone length, quantity, hooks, and spacing application remain deterministic."),
        _det("PIECE_GENERATION", "Piece generation remains deterministic."),
        _det("WEIGHT", "Steel weight remains deterministic."),
        _det("BBS", "BBS remains deterministic."),
        _det("WORKBOOK", "Excel/workbook remains production/deterministic. No routing in D.1.", engineering=False),
    ]
    by_name = {f["field_name"]: f for f in fields}
    return {
        "contract_version": CONTRACT_VERSION,
        "vision_preferred_neq_unconditionally_accepted": True,
        "confidence_threshold_config_key": "VISION_MIN_CONFIDENCE",
        "vision_min_confidence": VISION_MIN_CONFIDENCE,
        "fields": fields,
        "by_name": by_name,
        "vision_preferred_fields": list(VISION_PREFERRED_FIELDS),
        "deterministic_authority_fields": list(DETERMINISTIC_AUTHORITY_FIELDS),
        "hooks": {
            "LONGER_BAR_LIKELY_MAIN": {
                "status": "ARCHITECTURE_HOOK_ONLY",
                "implemented_override": False,
                "note": "Later phase may use relative span as a confidence signal. D.1 must not force longest=MAIN.",
            }
        },
    }


def field_authority(field_name: str) -> str:
    rec = authority_contract()["by_name"].get(field_name) or {}
    return str(rec.get("authority") or AUTH_DET)


def is_vision_preferred(field_name: str) -> bool:
    return field_authority(field_name) == AUTH_VISION


__all__ = [
    "DETERMINISTIC_AUTHORITY_FIELDS",
    "VISION_PREFERRED_FIELDS",
    "authority_contract",
    "field_authority",
    "is_vision_preferred",
]
