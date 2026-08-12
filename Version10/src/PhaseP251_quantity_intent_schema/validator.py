"""Deterministic Quantity Intent validation rules QI-001 … QI-010."""
from __future__ import annotations

from typing import List

from .config import (
    SEM_LONGITUDINAL_BAR,
    SEM_STIRRUP,
    STATUS_COMPOSITE,
    STATUS_EXPLICIT,
    STATUS_SPACING_BASED,
    STATUS_UNRESOLVED,
    VALIDATION_FAIL,
    VALIDATION_PARTIAL,
    VALIDATION_PASS,
)
from .models import QuantityIntent


def validate_intent(intent: QuantityIntent) -> QuantityIntent:
    reasons: List[str] = []
    parse_note = str(intent.provenance.get("parse_note") or "")

    # QI-009: raw text never discarded
    if not (intent.raw_text or "").strip():
        reasons.append("QI-009_MISSING_RAW_TEXT")

    # QI-007: provenance
    if not intent.evidence_links or not intent.evidence_links.has_provenance:
        reasons.append("QI-007_MISSING_PROVENANCE")

    # QI-006: rejected cannot be accepted
    if not intent.accepted:
        reasons.append("QI-006_REJECTED_EVIDENCE")

    # QI-001: explicit quantity positive integer
    if intent.quantity_status == STATUS_EXPLICIT:
        if intent.quantity_value is None or intent.quantity_value <= 0:
            reasons.append("QI-001_EXPLICIT_QUANTITY_INVALID")

    # QI-002: diameter positive when present
    if intent.diameter_value_mm is not None and intent.diameter_value_mm <= 0:
        reasons.append("QI-002_DIAMETER_INVALID")

    # QI-003: spacing-based must not carry longitudinal quantity_value
    if intent.quantity_status == STATUS_SPACING_BASED or intent.semantic_type == SEM_STIRRUP:
        if intent.quantity_value is not None:
            reasons.append("QI-003_STIRRUP_HAS_LONGITUDINAL_QUANTITY")
        if intent.quantity_status == STATUS_SPACING_BASED and (
            intent.leg_count is None or intent.leg_count <= 0
        ):
            reasons.append("QI-003_STIRRUP_MISSING_LEGS")

    # QI-004: composite preserves components
    if intent.quantity_status == STATUS_COMPOSITE:
        if len(intent.components) < 2:
            reasons.append("QI-004_COMPOSITE_MISSING_COMPONENTS")
        if intent.quantity_value is not None:
            reasons.append("QI-004_COMPOSITE_FLATTENED")

    # QI-005: ambiguous remain unresolved
    if "AMBIGUOUS_QUANTITY" in parse_note:
        if intent.quantity_status != STATUS_UNRESOLVED:
            reasons.append("QI-005_AMBIGUOUS_NOT_UNRESOLVED")
        if intent.quantity_value is not None:
            reasons.append("QI-005_AMBIGUOUS_HAS_VALUE")

    # QI-008: quantity and diameter remain separate; explicit bar should have diameter
    if (
        intent.quantity_status == STATUS_EXPLICIT
        and intent.quantity_value is not None
        and intent.diameter_value_mm is None
        and intent.semantic_type == SEM_LONGITUDINAL_BAR
    ):
        reasons.append("QI-008_MISSING_DIAMETER_FOR_EXPLICIT_BAR")

    # QI-010: no engineering calculation fields
    for banned in ("cut_length", "steel_weight", "piece_count_engineered"):
        if banned in intent.provenance:
            reasons.append("QI-010_ENGINEERING_FIELD_PRESENT")

    hard = {
        "QI-001_EXPLICIT_QUANTITY_INVALID",
        "QI-006_REJECTED_EVIDENCE",
        "QI-009_MISSING_RAW_TEXT",
        "QI-003_STIRRUP_HAS_LONGITUDINAL_QUANTITY",
        "QI-005_AMBIGUOUS_HAS_VALUE",
        "QI-010_ENGINEERING_FIELD_PRESENT",
    }
    if any(r in hard for r in reasons) or not intent.accepted:
        intent.validation_status = VALIDATION_FAIL
    elif reasons:
        intent.validation_status = VALIDATION_PARTIAL
    else:
        intent.validation_status = VALIDATION_PASS

    intent.validation_reasons = reasons
    return intent
