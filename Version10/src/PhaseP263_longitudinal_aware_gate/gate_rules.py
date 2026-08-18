"""
P2.6.3 CALL / SKIP / HOLD rules.

Stirrup path is frozen from P2.6.2. Longitudinal uses coverage classification.
Production signals only. No stratum. No GT.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .config import (
    CALL_REASONS,
    COVER_DIA,
    COVER_LAYER,
    COVER_MISSING,
    COVER_MULTI,
    COVER_QTY,
    COVER_ROLE,
    DECISION_CALL,
    DECISION_HOLD,
    DECISION_SKIP,
    GATE_VERSION,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    SKIP_REASONS,
)
from .policy import assert_no_forbidden_reason

_LONG_SHORTFALL = {COVER_QTY, COVER_MULTI, COVER_LAYER, COVER_MISSING}
_LONG_CONFLICT = {COVER_ROLE, COVER_DIA}


def _hint(feat: Dict[str, Any], call_reasons: List[str]) -> str:
    if "STIRRUP_TEXT_NO_OBJECT" in call_reasons or "OCR_CORRUPTED_STIRRUP" in call_reasons:
        return "STIRRUP"
    if any(
        r in call_reasons
        for r in (
            "MISSING_DETERMINISTIC_OBJECT",
            "LONGITUDINAL_COVERAGE_SHORTFALL",
            "LONGITUDINAL_SEMANTIC_CONFLICT",
        )
    ):
        return "LONGITUDINAL_REINFORCEMENT"
    if feat.get("side_text_present") and not feat.get("side_object_present"):
        return "SIDE_FACE_REINFORCEMENT"
    return "OTHER"


def _frozen_stirrup_calls(features: Dict[str, Any], call: List[str]) -> None:
    """Exact P2.6.2 stirrup CALL conditions. Do not redesign."""
    if features.get("stirrup_text_no_object") or (
        int(features.get("unmatched_stirrup_count") or 0) > 0
        and not features.get("stirrup_object_present")
    ):
        call.append("STIRRUP_TEXT_NO_OBJECT")
    if int(features.get("ocr_corrupted_stirrup_unmatched") or 0) > 0 or (
        int(features.get("OCR_corruption_count") or 0) > 0
        and features.get("stirrup_text_present")
        and not features.get("stirrup_object_present")
    ):
        call.append("OCR_CORRUPTED_STIRRUP")
    incomplete = int(features.get("incomplete_parse_count") or 0) > 0
    stirrup_gap = bool(features.get("stirrup_text_present")) and not features.get(
        "stirrup_object_present"
    )
    if incomplete and stirrup_gap:
        call.append("INCOMPLETE_PARSE")


def decide_gate(features: Dict[str, Any]) -> Dict[str, Any]:
    if "stratum" in features:
        raise ValueError("stratum must not be used as a gate feature")
    call: List[str] = []
    skip: List[str] = []
    hold: List[str] = []
    assoc = str(features.get("association") or "TARGET_BEAM").upper()

    _frozen_stirrup_calls(features, call)

    cov = str(features.get("longitudinal_coverage") or "")
    if cov == COVER_MISSING:
        call.append("MISSING_DETERMINISTIC_OBJECT")
    elif cov in _LONG_CONFLICT:
        call.append("LONGITUDINAL_SEMANTIC_CONFLICT")
    elif cov in _LONG_SHORTFALL:
        call.append("LONGITUDINAL_COVERAGE_SHORTFALL")

    if int(features.get("unassociated_strong_count") or 0) > 0 and (
        not features.get("stirrup_object_present") or features.get("stirrup_text_no_object")
    ):
        call.append("UNASSOCIATED_REINFORCEMENT")
    if (
        features.get("side_text_present")
        and not features.get("side_object_present")
        and not call
    ):
        call.append("OTHER")

    if assoc == "OTHER_BEAM":
        hold.append("OTHER_BEAM_ASSOCIATION")
    elif assoc == "UNCERTAIN" and not call:
        hold.append("UNCERTAIN_ASSOCIATION")
    elif (
        int(features.get("unassociated_annotation_count") or 0) > 0
        and not call
        and int(features.get("matching_object_count") or 0) == 0
    ):
        hold.append("UNASSOCIATED_REINFORCEMENT")

    call = list(dict.fromkeys(call))
    for r in call:
        assert_no_forbidden_reason(r)
        if r not in CALL_REASONS:
            raise ValueError(f"unsupported CALL reason: {r}")

    if call and "OTHER_BEAM_ASSOCIATION" not in hold:
        if "STIRRUP_TEXT_NO_OBJECT" in call or "OCR_CORRUPTED_STIRRUP" in call:
            priority = PRIORITY_HIGH
            strength = "HIGH"
        elif (
            "INCOMPLETE_PARSE" in call
            or "MISSING_DETERMINISTIC_OBJECT" in call
            or "LONGITUDINAL_COVERAGE_SHORTFALL" in call
            or "LONGITUDINAL_SEMANTIC_CONFLICT" in call
        ):
            priority = PRIORITY_MEDIUM
            strength = "MEDIUM"
        else:
            priority = PRIORITY_LOW
            strength = "LOW"
        decision = DECISION_CALL
        reasons = call
    elif hold:
        decision = DECISION_HOLD
        priority = PRIORITY_LOW
        strength = "LOW"
        reasons = hold
    else:
        decision = DECISION_SKIP
        priority = PRIORITY_LOW
        strength = "LOW"
        if cov == "FULLY_COVERED":
            skip.append("LONGITUDINAL_FULLY_COVERED")
        if int(features.get("matching_object_count") or 0) > 0:
            skip.append("MATCHING_OBJECT_EXISTS")
        if features.get("parse_complete"):
            skip.append("COMPLETE_PARSE")
        if int(features.get("deterministic_object_count") or 0) >= max(
            1, int(features.get("reinforcement_annotation_count") or 0)
        ) and int(features.get("matching_object_count") or 0) >= int(
            features.get("reinforcement_annotation_count") or 0
        ):
            skip.append("STRONG_DETERMINISTIC_COVERAGE")
        if not skip:
            skip.append("NO_PRODUCTION_GAP")
        reasons = list(dict.fromkeys(skip))
        for r in reasons:
            assert_no_forbidden_reason(r)
            if r not in SKIP_REASONS:
                raise ValueError(f"unsupported SKIP reason: {r}")

    return {
        "decision": decision,
        "priority": priority,
        "reason_codes": reasons,
        "evidence_strength": strength,
        "candidate_class_hint": _hint(features, call),
        "gate_version": GATE_VERSION,
    }


__all__ = ["decide_gate"]
