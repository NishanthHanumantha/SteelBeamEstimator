"""P2.5.11 enrichment gate. Consumes P2.5.10; does not bypass it."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PhaseP2510_new_stirrup_safety.beam_safety_gate import gate_beam as p2510_gate_beam
from PhaseP2510_new_stirrup_safety.config import CLS_NO_NEW, CLS_SUPPLEMENT

from .config import (
    DEC_ALLOW,
    DEC_HOLD,
    DEC_REJECT,
    QUALITY_CLEAN,
    QUALITY_MALFORMED,
    QUALITY_OCR,
    REASON_COMPLETE_SCHEDULE,
    REASON_INSUFFICIENT,
    REASON_INVALID_DIAMETER,
    REASON_INVALID_LEGS,
    REASON_INVALID_SPACING,
    REASON_MALFORMED,
    REASON_NO_NOTATION,
    REASON_OCR_TRUNCATED,
    REASON_PLAUSIBILITY,
    REASON_PRESERVE_P2510_ALLOW,
    REASON_PRESERVE_P2510_REJECT,
    REASON_TARGET_ASSOC,
    REASON_UNSUPPORTED_NEW,
    REASON_VALID_NOTATION,
    REASON_VALID_UNIFORM,
    REASON_WEAK_ASSOC,
    STRENGTH_STRONG,
    STRENGTH_UNSAFE,
)
from .evidence_resolver import assert_runtime_context, resolve_evidence_strength
from .notation_quality import field_validity
from .policy import load_enrichment_config

_ERR_MAP = {
    "DIAMETER": REASON_INVALID_DIAMETER,
    "LEGS": REASON_INVALID_LEGS,
    "SPACING": REASON_INVALID_SPACING,
}


def _map_field_errors(errors: List[str]) -> List[str]:
    out: List[str] = []
    for e in errors:
        mapped = None
        for frag, code in _ERR_MAP.items():
            if frag in e:
                mapped = code
                break
        out.append(mapped or e)
    return out


def enrich_decision(
    *,
    p2510_result: Dict[str, Any],
    ctx: Dict[str, Any],
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Upgrade a P2.5.10 HOLD when notation evidence is strong. Never invent stirrups."""
    assert_runtime_context(ctx)
    cfg = cfg or load_enrichment_config()
    p2510_dec = p2510_result.get("decision")
    classification = p2510_result.get("classification")
    validity = field_validity(
        diameter=ctx.get("vis_diameter"),
        legs=ctx.get("vis_legs"),
        spacing=ctx.get("vis_spacing") or [],
    )
    resolved = resolve_evidence_strength(ctx=ctx, validity=validity, cfg=cfg)
    reasons = list(resolved.get("reason_codes") or [])
    field_errs = _map_field_errors(list(validity.get("errors") or []))

    if cfg.get("preserve_p2510_allow", True) and p2510_dec == DEC_ALLOW:
        return {
            "decision": DEC_ALLOW,
            "p2510_decision": p2510_dec,
            "classification": classification,
            "evidence_strength": resolved.get("strength"),
            "reason_codes": [REASON_PRESERVE_P2510_ALLOW] + reasons,
            "resolved": resolved,
            "insertion": p2510_result.get("insertion"),
            "p2510": p2510_result,
        }
    if cfg.get("preserve_p2510_reject", True) and p2510_dec == DEC_REJECT:
        assoc = str(ctx.get("vis_association") or "")
        p2510_reasons = list(p2510_result.get("reason_codes") or [])
        if assoc == "UNCERTAIN" and all("ASSOCIATION" in c or "BEAM_ASSOCIATION" in c for c in p2510_reasons):
            return {
                "decision": DEC_HOLD,
                "p2510_decision": p2510_dec,
                "classification": classification,
                "evidence_strength": resolved.get("strength"),
                "reason_codes": [REASON_WEAK_ASSOC],
                "resolved": resolved,
                "insertion": p2510_result.get("insertion"),
                "p2510": p2510_result,
            }
        return {
            "decision": DEC_REJECT,
            "p2510_decision": p2510_dec,
            "classification": classification,
            "evidence_strength": resolved.get("strength") or STRENGTH_UNSAFE,
            "reason_codes": [REASON_PRESERVE_P2510_REJECT] + p2510_reasons + field_errs,
            "resolved": resolved,
            "insertion": p2510_result.get("insertion"),
            "p2510": p2510_result,
        }

    if classification in (CLS_NO_NEW, CLS_SUPPLEMENT) and p2510_dec == DEC_ALLOW:
        return {
            "decision": DEC_ALLOW,
            "p2510_decision": p2510_dec,
            "classification": classification,
            "evidence_strength": resolved.get("strength"),
            "reason_codes": reasons,
            "resolved": resolved,
            "insertion": p2510_result.get("insertion"),
            "p2510": p2510_result,
        }

    if field_errs:
        return {
            "decision": DEC_REJECT,
            "p2510_decision": p2510_dec,
            "classification": classification,
            "evidence_strength": STRENGTH_UNSAFE,
            "reason_codes": field_errs,
            "resolved": resolved,
            "insertion": p2510_result.get("insertion"),
            "p2510": p2510_result,
        }

    assoc = str(ctx.get("vis_association") or "")
    if assoc in ("OTHER_BEAM",):
        return {
            "decision": DEC_REJECT,
            "p2510_decision": p2510_dec,
            "classification": classification,
            "evidence_strength": STRENGTH_UNSAFE,
            "reason_codes": [REASON_WEAK_ASSOC],
            "resolved": resolved,
            "insertion": p2510_result.get("insertion"),
            "p2510": p2510_result,
        }
    if assoc in ("", "UNCERTAIN"):
        return {
            "decision": DEC_HOLD,
            "p2510_decision": p2510_dec,
            "classification": classification,
            "evidence_strength": resolved.get("strength"),
            "reason_codes": [REASON_WEAK_ASSOC],
            "resolved": resolved,
            "insertion": p2510_result.get("insertion"),
            "p2510": p2510_result,
        }

    quality = str(ctx.get("annotation_quality") or "")
    ocr_cfg = cfg.get("ocr") if isinstance(cfg.get("ocr"), dict) else {}
    if quality == QUALITY_OCR and ocr_cfg.get("treat_glyph_uniform_as_truncated", True):
        return {
            "decision": DEC_HOLD,
            "p2510_decision": p2510_dec,
            "classification": classification,
            "evidence_strength": resolved.get("strength"),
            "reason_codes": [REASON_OCR_TRUNCATED, REASON_UNSUPPORTED_NEW],
            "resolved": resolved,
            "insertion": p2510_result.get("insertion"),
            "p2510": p2510_result,
        }
    if quality == QUALITY_MALFORMED or not ctx.get("notation_parseable"):
        if not ctx.get("notation_parseable") and ctx.get("engineering_plausible"):
            return {
                "decision": DEC_HOLD,
                "p2510_decision": p2510_dec,
                "classification": classification,
                "evidence_strength": resolved.get("strength"),
                "reason_codes": [REASON_NO_NOTATION, REASON_PLAUSIBILITY],
                "resolved": resolved,
                "insertion": p2510_result.get("insertion"),
                "p2510": p2510_result,
            }
        return {
            "decision": DEC_HOLD if p2510_dec == DEC_HOLD else DEC_REJECT,
            "p2510_decision": p2510_dec,
            "classification": classification,
            "evidence_strength": STRENGTH_UNSAFE,
            "reason_codes": [REASON_MALFORMED],
            "resolved": resolved,
            "insertion": p2510_result.get("insertion"),
            "p2510": p2510_result,
        }

    strong_cfg = cfg.get("strong") if isinstance(cfg.get("strong"), dict) else {}
    moderate_cfg = cfg.get("moderate") if isinstance(cfg.get("moderate"), dict) else {}
    strength = resolved.get("strength")
    if strength == STRENGTH_STRONG:
        allow_clean = bool(strong_cfg.get("allow_clean_uniform_with_target_association", True))
        allow_sched = bool(strong_cfg.get("allow_visible_schedule", True))
        if (quality == QUALITY_CLEAN and allow_clean) or (resolved.get("complete_schedule") and allow_sched):
            codes = [REASON_VALID_NOTATION, REASON_TARGET_ASSOC]
            if quality == QUALITY_CLEAN:
                codes.insert(0, REASON_VALID_UNIFORM)
            if resolved.get("complete_schedule"):
                codes.insert(0, REASON_COMPLETE_SCHEDULE)
            if ctx.get("engineering_plausible"):
                codes.append(REASON_PLAUSIBILITY)
            return {
                "decision": DEC_ALLOW,
                "p2510_decision": p2510_dec,
                "classification": classification,
                "evidence_strength": STRENGTH_STRONG,
                "reason_codes": codes,
                "resolved": resolved,
                "insertion": p2510_result.get("insertion"),
                "p2510": p2510_result,
            }

    if (
        strength == "MODERATE"
        and moderate_cfg.get("allow_clean_uniform_with_plausibility", True)
        and quality == QUALITY_CLEAN
        and ctx.get("engineering_plausible")
        and assoc == "TARGET_BEAM"
    ):
        return {
            "decision": DEC_ALLOW,
            "p2510_decision": p2510_dec,
            "classification": classification,
            "evidence_strength": "MODERATE",
            "reason_codes": [REASON_VALID_UNIFORM, REASON_PLAUSIBILITY, REASON_TARGET_ASSOC],
            "resolved": resolved,
            "insertion": p2510_result.get("insertion"),
            "p2510": p2510_result,
        }

    return {
        "decision": DEC_HOLD,
        "p2510_decision": p2510_dec,
        "classification": classification,
        "evidence_strength": resolved.get("strength"),
        "reason_codes": [REASON_INSUFFICIENT] + reasons,
        "resolved": resolved,
        "insertion": p2510_result.get("insertion"),
        "p2510": p2510_result,
    }


def filter_promoted_enriched(
    *,
    r13_doc: Dict[str, Any],
    audits: List[Dict[str, Any]],
    promoted: List[Dict[str, Any]],
    p2510_contexts: Dict[str, Dict[str, Any]],
    p2511_contexts: Dict[str, Dict[str, Any]],
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    cfg = cfg or load_enrichment_config()
    by_beam: Dict[str, List[Dict[str, Any]]] = {}
    for rec in promoted:
        by_beam.setdefault(str(rec.get("beam_id")), []).append(rec)
    decisions: List[Dict[str, Any]] = []
    allowed: List[Dict[str, Any]] = []
    for beam_id, recs in by_beam.items():
        p2510_ctx = p2510_contexts.get(beam_id) or {}
        p2511_ctx = p2511_contexts.get(beam_id) or {}
        p2510 = p2510_gate_beam(
            r13_doc=r13_doc,
            audits=audits,
            promoted=recs,
            beam_id=beam_id,
            ctx=p2510_ctx,
        )
        result = enrich_decision(p2510_result=p2510, ctx=p2511_ctx, cfg=cfg)
        result["beam_id"] = beam_id
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


__all__ = ["enrich_decision", "filter_promoted_enriched"]
