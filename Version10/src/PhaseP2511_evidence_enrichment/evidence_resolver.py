"""P2.5.11 evidence resolver. Runtime — production signals only."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from PhaseP2510_new_stirrup_safety.evidence_evaluator import (
    complete_schedule_in_text,
    peer_agreement_count,
)

from .config import (
    QUALITY_CLEAN,
    QUALITY_MALFORMED,
    QUALITY_OCR,
    QUALITY_SCHEDULE,
    RUNTIME_CONTEXT_KEYS,
    STRENGTH_MODERATE,
    STRENGTH_STRONG,
    STRENGTH_UNSAFE,
    STRENGTH_WEAK,
)
from .notation_quality import (
    classify_annotation_quality,
    field_validity,
    parse_notation,
    slash_schedule_in_text,
    vision_matches_notation,
)
from .policy import load_enrichment_config


def assert_runtime_context(context: Optional[Dict[str, Any]]) -> None:
    if not context:
        return
    for key in context.keys():
        if key not in RUNTIME_CONTEXT_KEYS:
            raise ValueError(f"unsupported runtime context key: {key!r}")


def _as_list(v: Any) -> List[int]:
    out: List[int] = []
    for x in v or []:
        try:
            out.append(int(round(float(x))))
        except Exception:
            continue
    return out


def build_enrichment_context(
    *,
    beam: Optional[Dict[str, Any]],
    audit: Dict[str, Any],
    peer_audits: Optional[Sequence[Dict[str, Any]]] = None,
    owned_by_beam: bool = False,
) -> Dict[str, Any]:
    geom = (beam or {}).get("geometry") or {}
    stirrups = [b for b in ((beam or {}).get("stirrups") or []) if isinstance(b, dict)]
    vis = audit.get("vision_result") or {}
    det = audit.get("deterministic_result") or {}
    links = det.get("evidence_links") or {}
    text = str(audit.get("annotation_text") or "")
    vis_spacing = _as_list(vis.get("spacing_mm"))
    notation = parse_notation(text)
    quality = classify_annotation_quality(text)
    vis_dia = vis.get("diameter_mm")
    vis_legs = vis.get("legs")
    match = vision_matches_notation(
        vis_diameter=vis_dia, vis_legs=vis_legs, vis_spacing=vis_spacing, notation=notation
    )
    leader = links.get("leader_id")
    chain = str(links.get("chain_semantic_type") or "")
    top_n = len((beam or {}).get("top_main_bars") or [])
    bot_n = len((beam or {}).get("bottom_main_bars") or [])
    ctx = {
        "beam_id": str((beam or {}).get("beam_id") or audit.get("beam_id") or ""),
        "span_mm": geom.get("clear_span_mm") or geom.get("span_mm"),
        "stirrup_count": len(stirrups),
        "has_stirrups": len(stirrups) > 0,
        "top_main_count": top_n,
        "bottom_main_count": bot_n,
        "side_face_count": len((beam or {}).get("side_face_reinforcement") or []),
        "annotation_text": text,
        "annotation_id": str(audit.get("annotation_id") or ""),
        "candidate_id": str(audit.get("candidate_id") or ""),
        "det_semantic_type": str(det.get("semantic_type") or ""),
        "vis_semantic_type": str(vis.get("semantic_type") or ""),
        "vis_role": str(vis.get("role") or ""),
        "vis_association": str(vis.get("beam_association") or ""),
        "vis_diameter": vis_dia,
        "vis_legs": vis_legs,
        "vis_spacing": vis_spacing,
        "vis_quantity": vis.get("quantity"),
        "vis_normalized_notation": str(vis.get("normalized_notation") or ""),
        "trigger_reason": list(audit.get("shadow_trigger_reason") or []),
        "owned_by_beam": bool(owned_by_beam),
        "has_leader": bool(leader),
        "chain_semantic_stirrup": chain.upper() == "STIRRUPNOTE" or "STIRRUP" in chain.upper(),
        "peer_agreement_count": peer_agreement_count(audit=audit, peer_audits=peer_audits or []),
        "complete_schedule_in_text": complete_schedule_in_text(text, vis_spacing),
        "numeric_slash_schedule_in_text": slash_schedule_in_text(text),
        "annotation_quality": quality,
        "notation_parseable": bool(notation.get("raw_parseable") or notation.get("stripped_parseable")),
        "notation_legs": notation.get("legs"),
        "notation_diameter": notation.get("diameter_mm"),
        "notation_spacing": notation.get("spacings_mm"),
        "engineering_plausible": (top_n + bot_n) > 0,
        "spatial_support": bool(leader) or bool(owned_by_beam),
        "contextual_support": int(peer_agreement_count(audit=audit, peer_audits=peer_audits or [])) >= 1
        or (chain.upper() == "STIRRUPNOTE"),
        "fields_match_notation": match,
    }
    assert_runtime_context(ctx)
    return ctx


def resolve_evidence_strength(
    *,
    ctx: Dict[str, Any],
    validity: Dict[str, Any],
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Hierarchy: valid associated notation is strong; glyph-uniform OCR is weak."""
    cfg = cfg or load_enrichment_config()
    quality = str(ctx.get("annotation_quality") or "")
    assoc = str(ctx.get("vis_association") or "")
    target = assoc == "TARGET_BEAM"
    vis_type = str(ctx.get("vis_semantic_type") or "")
    det_type = str(ctx.get("det_semantic_type") or "")
    role = str(ctx.get("vis_role") or "")
    stirrup_role = vis_type in ("STIRRUP", "") and role in ("STIRRUP", "", "UNKNOWN")
    if det_type and det_type != "STIRRUP" and vis_type == "STIRRUP":
        stirrup_role = False
    valid_fields = bool(validity.get("diameter_ok") and validity.get("legs_ok") and validity.get("spacing_ok"))
    match = bool(ctx.get("fields_match_notation"))
    parseable = bool(ctx.get("notation_parseable"))
    plausible = bool(ctx.get("engineering_plausible"))
    spatial = bool(ctx.get("spatial_support"))
    schedule = quality == QUALITY_SCHEDULE or bool(ctx.get("complete_schedule_in_text"))
    clean = quality == QUALITY_CLEAN
    ocr = quality == QUALITY_OCR
    malformed = quality == QUALITY_MALFORMED
    conflict = assoc in ("OTHER_BEAM", "UNCERTAIN")

    if conflict or not valid_fields or not stirrup_role:
        strength = STRENGTH_UNSAFE
    elif malformed or not parseable:
        strength = STRENGTH_UNSAFE
    elif schedule and target and valid_fields and match:
        strength = STRENGTH_STRONG
    elif clean and target and valid_fields and match:
        strength = STRENGTH_STRONG
    elif clean and valid_fields and match and plausible:
        strength = STRENGTH_MODERATE
    elif ocr:
        strength = STRENGTH_WEAK
    else:
        strength = STRENGTH_WEAK

    codes: List[str] = []
    if clean:
        codes.append("VALID_UNIFORM_STIRRUP" if len(ctx.get("notation_spacing") or []) <= 1 else "VALID_BEAM_STIRRUP_NOTATION")
    if schedule:
        codes.append("COMPLETE_STIRRUP_SCHEDULE")
    if target:
        codes.append("TARGET_BEAM_ASSOCIATION")
    if plausible:
        codes.append("ENGINEERING_PLAUSIBILITY")
    if spatial:
        codes.append("SPATIAL_SUPPORT")
    if ctx.get("contextual_support"):
        codes.append("CONTEXTUAL_SUPPORT")
    if ocr:
        codes.append("OCR_TRUNCATED")
    if malformed:
        codes.append("MALFORMED_STIRRUP_NOTATION")
    if not parseable:
        codes.append("NO_VALID_STIRRUP_NOTATION")
    if conflict:
        codes.append("WEAK_BEAM_ASSOCIATION")
    if not match and parseable:
        codes.append("CONTRADICTORY_EVIDENCE")

    return {
        "strength": strength,
        "annotation_quality": quality,
        "target_association": target,
        "valid_fields": valid_fields,
        "notation_valid": parseable and (clean or schedule),
        "engineering_plausibility": plausible,
        "spatial_evidence": spatial,
        "contextual_evidence": bool(ctx.get("contextual_support")),
        "complete_schedule": schedule,
        "fields_consistent": match,
        "reason_codes": codes,
        "validity": validity,
    }


__all__ = [
    "assert_runtime_context",
    "build_enrichment_context",
    "resolve_evidence_strength",
]
