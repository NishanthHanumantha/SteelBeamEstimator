"""Build QuantityIntent records from a P2.5 evidence package."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .classifier import classify_role, classify_semantic_type, confidence_for
from .config import STATUS_INVALID, STATUS_UNRESOLVED
from .evidence_linker import is_rejected_annotation, link_annotation_evidence
from .models import QuantityIntent
from .parser import normalize_text, parse_quantity_expression
from .validator import validate_intent


def intent_id_for(beam_id: str, annotation_id: str) -> str:
    return f"QI::{beam_id}::{annotation_id}"


def build_intent_for_annotation(
    *,
    beam_id: str,
    annotation: Dict[str, Any],
    evidence: Dict[str, Any],
) -> Optional[QuantityIntent]:
    aid = str(annotation.get("annotation_id") or "")
    raw = (annotation.get("raw_text") or annotation.get("normalized_text") or "").strip()
    if not aid:
        return None

    # QI-006: rejected annotations excluded
    if is_rejected_annotation(aid, evidence):
        return None

    links, ctx = link_annotation_evidence(
        beam_id=beam_id,
        annotation=annotation,
        evidence=evidence,
    )
    chain_sem = ctx.get("chain_semantic_type")
    parse = parse_quantity_expression(raw, chain_semantic_type=chain_sem)
    semantic_type = classify_semantic_type(parse, chain_semantic_type=chain_sem)
    role = classify_role(
        semantic_type=semantic_type,
        role_hint=ctx.get("role_hint"),
        chain=ctx.get("chain"),
    )
    conf = confidence_for(
        parse=parse,
        semantic_type=semantic_type,
        role=role,
        links_ok=links.has_provenance,
    )

    # spacing expression fill
    spacing_expr = parse.spacing_expression
    if parse.spacing_values_mm and not spacing_expr:
        spacing_expr = "/".join(str(int(x)) for x in parse.spacing_values_mm)

    intent = QuantityIntent(
        intent_id=intent_id_for(beam_id, aid),
        beam_id=beam_id,
        annotation_id=aid,
        raw_text=raw,
        normalized_text=normalize_text(raw),
        semantic_type=semantic_type,
        reinforcement_role=role,
        quantity_expression=parse.quantity_expression or raw,
        quantity_value=parse.quantity_value,
        quantity_status=parse.quantity_status or STATUS_UNRESOLVED,
        quantity_source=parse.quantity_source,
        diameter_expression=parse.diameter_expression,
        diameter_value_mm=parse.diameter_value_mm,
        spacing_expression=spacing_expr,
        spacing_value_mm=parse.spacing_value_mm,
        spacing_values_mm=list(parse.spacing_values_mm or []),
        leg_expression=parse.leg_expression,
        leg_count=parse.leg_count,
        unit=parse.unit,
        components=list(parse.components or []),
        evidence_links=links,
        confidence=conf,
        accepted=True,
        provenance={
            "phase": "P2.5.1",
            "parse_note": parse.parse_note,
            "ambiguous": parse.ambiguous,
            "source_evidence_phase": evidence.get("phase_id") or evidence.get("model_version"),
            "leader_id": links.leader_id,
            "ownership_id": links.ownership_id,
            "source_handle": links.source_handle,
            "evidence_id": links.evidence_id,
        },
    )
    return validate_intent(intent)


def build_intents_for_beam(evidence: Dict[str, Any]) -> List[QuantityIntent]:
    beam_id = str(evidence.get("beam_id") or "")
    intents: List[QuantityIntent] = []
    # Eligible = accepted annotations present in the evidence package
    for ann in evidence.get("annotations") or []:
        intent = build_intent_for_annotation(
            beam_id=beam_id,
            annotation=ann,
            evidence=evidence,
        )
        if intent is not None:
            intents.append(intent)
    # Deterministic order
    intents.sort(key=lambda x: (x.beam_id, x.annotation_id, x.intent_id))
    return intents
