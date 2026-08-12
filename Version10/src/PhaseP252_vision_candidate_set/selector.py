"""Deterministic Vision candidate selection from P2.5.1 QuantityIntents."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .classifier import (
    classify_intent_reasons,
    is_development_note,
    is_ocr_corrupted,
    is_sfr_descriptive_note,
    ocr_normalization_hint,
)
from .config import (
    OUTCOME_CANDIDATE,
    OUTCOME_DEFERRED,
    OUTCOME_EXCLUDED,
    P0,
    P1,
    P2,
    P3,
    REASON_DEFER_ENGINEERING_RULE,
    REASON_INSUFFICIENT_VISUAL_EVIDENCE,
    REASON_OCR_CORRUPTION,
    REASON_SEMANTIC_CONTEXT_REQUIRED,
    REASON_VISION_NOT_REQUIRED,
    VISION_STATUS_PENDING,
)


def candidate_id_for(beam_id: str, annotation_id: str) -> str:
    return f"VC::{beam_id}::{annotation_id}"


def _priority_for(reasons: List[str], outcome: str) -> str:
    if outcome != OUTCOME_CANDIDATE:
        if REASON_DEFER_ENGINEERING_RULE in reasons:
            return P3
        if REASON_SEMANTIC_CONTEXT_REQUIRED in reasons:
            return P2
        return P3
    if REASON_OCR_CORRUPTION in reasons:
        return P0  # material stirrup quantity impact likely
    if "AMBIGUOUS_QUANTITY" in reasons:
        return P1
    if "UNRESOLVED_QUANTITY" in reasons:
        return P1
    if REASON_SEMANTIC_CONTEXT_REQUIRED in reasons:
        return P2
    return P2


def select_from_intent(intent: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decide VISION_CANDIDATE / DEFERRED / EXCLUDED for one QuantityIntent.
    Explicit/successful stirrup parses are excluded (Vision not required).
    """
    beam_id = str(intent.get("beam_id") or "")
    annotation_id = str(intent.get("annotation_id") or "")
    raw = intent.get("raw_text") or ""
    status = intent.get("quantity_status") or ""
    reasons, reason_text = classify_intent_reasons(intent)

    # Default: resolved intents excluded
    if REASON_VISION_NOT_REQUIRED in reasons and status in (
        "EXPLICIT",
        "SPACING_BASED",
        "COMPOSITE",
    ):
        return {
            "candidate_id": candidate_id_for(beam_id, annotation_id),
            "outcome": OUTCOME_EXCLUDED,
            "candidate_priority": P3,
            "candidate_reason_codes": reasons,
            "candidate_reason_text": reason_text,
            "vision_status": VISION_STATUS_PENDING,
            "candidate_normalization_hint": None,
            "beam_id": beam_id,
            "annotation_id": annotation_id,
            "raw_text": raw,
        }

    # Development notes → deferred to engineering rules (not Vision quantity)
    if is_development_note(raw):
        return {
            "candidate_id": candidate_id_for(beam_id, annotation_id),
            "outcome": OUTCOME_DEFERRED,
            "candidate_priority": P3,
            "candidate_reason_codes": reasons,
            "candidate_reason_text": reason_text,
            "vision_status": VISION_STATUS_PENDING,
            "candidate_normalization_hint": None,
            "beam_id": beam_id,
            "annotation_id": annotation_id,
            "raw_text": raw,
        }

    # SFR descriptive notes → Vision semantic candidate (P2), not quantity
    if is_sfr_descriptive_note(raw):
        return {
            "candidate_id": candidate_id_for(beam_id, annotation_id),
            "outcome": OUTCOME_CANDIDATE,
            "candidate_priority": P2,
            "candidate_reason_codes": reasons,
            "candidate_priority_note": "semantic_context_not_quantity",
            "candidate_reason_text": reason_text,
            "vision_status": VISION_STATUS_PENDING,
            "candidate_normalization_hint": None,
            "beam_id": beam_id,
            "annotation_id": annotation_id,
            "raw_text": raw,
        }

    # OCR / unresolved reinforcement → Vision candidate
    if is_ocr_corrupted(raw) or status == "UNRESOLVED":
        outcome = OUTCOME_CANDIDATE
        pri = _priority_for(reasons, outcome)
        return {
            "candidate_id": candidate_id_for(beam_id, annotation_id),
            "outcome": outcome,
            "candidate_priority": pri,
            "candidate_reason_codes": reasons,
            "candidate_reason_text": reason_text,
            "vision_status": VISION_STATUS_PENDING,
            "candidate_normalization_hint": ocr_normalization_hint(raw),
            "beam_id": beam_id,
            "annotation_id": annotation_id,
            "raw_text": raw,
        }

    return {
        "candidate_id": candidate_id_for(beam_id, annotation_id),
        "outcome": OUTCOME_EXCLUDED,
        "candidate_priority": P3,
        "candidate_reason_codes": [REASON_VISION_NOT_REQUIRED],
        "candidate_reason_text": "No selection rule matched",
        "vision_status": VISION_STATUS_PENDING,
        "candidate_normalization_hint": None,
        "beam_id": beam_id,
        "annotation_id": annotation_id,
        "raw_text": raw,
    }


def select_candidates(intents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate by beam_id+annotation_id; deterministic order."""
    seen = set()
    out: List[Dict[str, Any]] = []
    for intent in sorted(
        intents,
        key=lambda x: (str(x.get("beam_id") or ""), str(x.get("annotation_id") or "")),
    ):
        key = (str(intent.get("beam_id") or ""), str(intent.get("annotation_id") or ""))
        if key in seen or not key[0] or not key[1]:
            continue
        seen.add(key)
        rec = select_from_intent(intent)
        rec["deterministic_intent"] = {
            "intent_id": intent.get("intent_id"),
            "raw_text": intent.get("raw_text"),
            "normalized_text": intent.get("normalized_text"),
            "quantity_status": intent.get("quantity_status"),
            "quantity_value": intent.get("quantity_value"),
            "diameter_value_mm": intent.get("diameter_value_mm"),
            "semantic_type": intent.get("semantic_type"),
            "reinforcement_role": intent.get("reinforcement_role"),
            "leg_count": intent.get("leg_count"),
            "spacing_value_mm": intent.get("spacing_value_mm"),
            "spacing_values_mm": intent.get("spacing_values_mm"),
            "validation_status": intent.get("validation_status"),
            "evidence_links": intent.get("evidence_links"),
            "confidence": intent.get("confidence"),
        }
        out.append(rec)
    return out


def mark_insufficient_visual(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Downgrade a candidate to DEFERRED when visual evidence is missing."""
    updated = dict(rec)
    updated["outcome"] = OUTCOME_DEFERRED
    codes = list(updated.get("candidate_reason_codes") or [])
    if REASON_INSUFFICIENT_VISUAL_EVIDENCE not in codes:
        codes.append(REASON_INSUFFICIENT_VISUAL_EVIDENCE)
    updated["candidate_reason_codes"] = codes
    updated["candidate_reason_text"] = (
        (updated.get("candidate_reason_text") or "")
        + " | deferred: insufficient verified visual evidence"
    ).strip(" |")
    updated["candidate_priority"] = P3
    return updated
