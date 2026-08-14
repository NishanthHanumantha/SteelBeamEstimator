"""P2.5.10 insertion safety gate. ALLOW / HOLD / REJECT from production evidence only."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import (
    CLS_CREATES_NEW,
    CLS_NO_NEW,
    CLS_SUPPLEMENT,
    DEC_ALLOW,
    DEC_HOLD,
    DEC_REJECT,
    REASON_ASSOCIATION_CONFLICT,
    REASON_INCOMPATIBLE_STIRRUP,
    REASON_INSUFFICIENT_EVIDENCE,
    REASON_INVALID_DIAMETER,
    REASON_INVALID_LEGS,
    REASON_INVALID_SPACING,
    REASON_INVENTED_QUANTITY,
    REASON_NEW_PIECE_NO_STIRRUP,
    REASON_NEW_REQUIRES_STRONGER,
    REASON_NEW_STEEL_NO_EVIDENCE,
    REASON_NEW_SUPPORTED,
    REASON_NEW_ZONE_NO_EXISTING,
    REASON_NO_NEW_SAFE,
    REASON_PRODUCTION_MUTATION,
    REASON_SEMANTIC_CONFLICT,
    REASON_SUPPLEMENT_SAFE,
    REASON_UNSUPPORTED_NEW_STIRRUP,
    REASON_UNSUPPORTED_NEW_ZONE,
    REASON_UNSUPPORTED_TRANSFORM,
)
from .evidence_evaluator import assert_runtime_context, evaluate_insertion_evidence
from .insertion_classifier import classify_insertion
from .policy import load_insertion_config

_HARD_MAP = {
    "INVALID_DIAMETER": REASON_INVALID_DIAMETER,
    "DIAMETER_NOT_NUMERIC": REASON_INVALID_DIAMETER,
    "DIAMETER_NOT_POSITIVE": REASON_INVALID_DIAMETER,
    "DIAMETER_OUT_OF_CONVENTIONAL_RANGE": REASON_INVALID_DIAMETER,
    "DIAMETER_NOT_WHOLE_MM": REASON_INVALID_DIAMETER,
    "DIAMETER_NOT_CONVENTIONAL": REASON_INVALID_DIAMETER,
    "INVALID_LEGS": REASON_INVALID_LEGS,
    "LEGS_NOT_INTEGER": REASON_INVALID_LEGS,
    "LEGS_NOT_POSITIVE": REASON_INVALID_LEGS,
    "LEGS_OUT_OF_RANGE": REASON_INVALID_LEGS,
    "INVALID_SPACING": REASON_INVALID_SPACING,
    "SPACING_MISSING": REASON_INVALID_SPACING,
    "SPACING_NOT_LIST": REASON_INVALID_SPACING,
    "SPACING_EMPTY": REASON_INVALID_SPACING,
    "SPACING_SEQUENCE_TOO_LONG": REASON_INVALID_SPACING,
    "SPACING_NOT_NUMERIC": REASON_INVALID_SPACING,
    "SPACING_NOT_POSITIVE": REASON_INVALID_SPACING,
    "SPACING_OUT_OF_RANGE": REASON_INVALID_SPACING,
    "INVENTED_QUANTITY": REASON_INVENTED_QUANTITY,
    "DETERMINISTIC_SEMANTIC_CONFLICT": REASON_SEMANTIC_CONFLICT,
    "BEAM_ASSOCIATION_CONFLICT": REASON_ASSOCIATION_CONFLICT,
    "INCOMPATIBLE_EXISTING_STIRRUP": REASON_INCOMPATIBLE_STIRRUP,
    "PRODUCTION_MUTATION_ATTEMPT": REASON_PRODUCTION_MUTATION,
}


def _map_hard(code: str) -> str:
    return _HARD_MAP.get(code, code)


def decide_insertion(
    *,
    classification: Dict[str, Any],
    evidence: Dict[str, Any],
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    cfg = cfg or load_insertion_config()
    new_cfg = cfg.get("creates_new_stirrup") if isinstance(cfg.get("creates_new_stirrup"), dict) else {}
    no_new_cfg = cfg.get("no_new_stirrup") if isinstance(cfg.get("no_new_stirrup"), dict) else {}
    supp_cfg = cfg.get("supplements_existing") if isinstance(cfg.get("supplements_existing"), dict) else {}

    hard = [_map_hard(c) for c in (evidence.get("hard_reasons") or [])]
    cls = classification.get("classification")
    codes: List[str] = list(hard)

    if hard:
        return {
            "decision": DEC_REJECT,
            "reason_codes": codes,
            "classification": cls,
        }

    if cls == CLS_NO_NEW:
        if no_new_cfg.get("allow", True):
            return {
                "decision": DEC_ALLOW,
                "reason_codes": [REASON_NO_NEW_SAFE],
                "classification": cls,
            }
        return {
            "decision": DEC_HOLD,
            "reason_codes": [REASON_INSUFFICIENT_EVIDENCE],
            "classification": cls,
        }

    if cls == CLS_SUPPLEMENT:
        if supp_cfg.get("follow_unknown_only", True):
            return {
                "decision": DEC_ALLOW,
                "reason_codes": [REASON_SUPPLEMENT_SAFE],
                "classification": cls,
            }
        return {
            "decision": DEC_HOLD,
            "reason_codes": [REASON_INSUFFICIENT_EVIDENCE],
            "classification": cls,
        }

    # CREATES_NEW_STIRRUP — stronger production evidence required.
    signals = evidence.get("signals") or {}
    annotation_supported_zone = bool(signals.get("complete_schedule_in_text"))
    hold_codes: List[str] = []
    unsupported_zone = bool(
        classification.get("new_zone")
        and not classification.get("existing_zone_match")
        and not annotation_supported_zone
    )
    if new_cfg.get("hold_if_new_zone_without_existing_zone", True) and unsupported_zone:
        hold_codes.append(REASON_NEW_ZONE_NO_EXISTING)
        if new_cfg.get("reject_uniform_to_variable_without_existing_zone", True):
            return {
                "decision": DEC_REJECT,
                "reason_codes": [REASON_UNSUPPORTED_NEW_ZONE, REASON_UNSUPPORTED_TRANSFORM],
                "classification": cls,
            }
    if (
        new_cfg.get("hold_if_new_piece_without_existing_stirrup", True)
        and classification.get("new_piece")
        and not classification.get("existing_stirrup_match")
        and not annotation_supported_zone
    ):
        hold_codes.append(REASON_NEW_PIECE_NO_STIRRUP)
    if (
        new_cfg.get("hold_if_new_steel_without_independent_evidence", True)
        and classification.get("new_steel")
        and not evidence.get("sufficient")
    ):
        hold_codes.append(REASON_NEW_STEEL_NO_EVIDENCE)

    if evidence.get("sufficient"):
        return {
            "decision": DEC_ALLOW,
            "reason_codes": [REASON_NEW_SUPPORTED],
            "classification": cls,
        }

    hold_codes.append(REASON_INSUFFICIENT_EVIDENCE)
    hold_codes.append(REASON_NEW_REQUIRES_STRONGER)
    if classification.get("new_stirrup_object"):
        hold_codes.append(REASON_UNSUPPORTED_NEW_STIRRUP)
    return {
        "decision": DEC_HOLD,
        "reason_codes": hold_codes,
        "classification": cls,
    }


def gate_beam(
    *,
    r13_doc: Dict[str, Any],
    audits: List[Dict[str, Any]],
    promoted: List[Dict[str, Any]],
    beam_id: str,
    ctx: Dict[str, Any],
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    assert_runtime_context(ctx)
    cfg = cfg or load_insertion_config()
    classification = classify_insertion(
        r13_doc=r13_doc,
        audits=audits,
        promoted=promoted,
        beam_id=beam_id,
        span_mm=ctx.get("span_mm"),
    )
    evidence = evaluate_insertion_evidence(
        ctx=ctx, classification=classification, promoted=promoted, cfg=cfg
    )
    gate = decide_insertion(classification=classification, evidence=evidence, cfg=cfg)
    return {
        "beam_id": beam_id,
        "classification": classification.get("classification"),
        "insertion": classification,
        "evidence": evidence,
        "decision": gate.get("decision"),
        "reason_codes": gate.get("reason_codes") or [],
    }


def filter_promoted(
    *,
    r13_doc: Dict[str, Any],
    audits: List[Dict[str, Any]],
    promoted: List[Dict[str, Any]],
    contexts: Dict[str, Dict[str, Any]],
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Keep P2.5.9 UNKNOWN-only promotions only when the insertion gate ALLOWs them."""
    cfg = cfg or load_insertion_config()
    by_beam: Dict[str, List[Dict[str, Any]]] = {}
    for rec in promoted:
        by_beam.setdefault(str(rec.get("beam_id")), []).append(rec)

    decisions: List[Dict[str, Any]] = []
    allowed: List[Dict[str, Any]] = []
    for beam_id, recs in by_beam.items():
        ctx = contexts.get(beam_id) or {}
        assert_runtime_context(ctx)
        result = gate_beam(
            r13_doc=r13_doc,
            audits=audits,
            promoted=recs,
            beam_id=beam_id,
            ctx=ctx,
            cfg=cfg,
        )
        decisions.append(result)
        if result.get("decision") == DEC_ALLOW:
            allowed.extend(recs)
    return {
        "allowed_promoted": allowed,
        "decisions": decisions,
        "allow_count": sum(1 for d in decisions if d.get("decision") == DEC_ALLOW),
        "hold_count": sum(1 for d in decisions if d.get("decision") == DEC_HOLD),
        "reject_count": sum(1 for d in decisions if d.get("decision") == DEC_REJECT),
    }


__all__ = ["decide_insertion", "filter_promoted", "gate_beam"]
