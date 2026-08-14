"""Production-available insertion evidence. Runtime module — no evaluation oracles."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

from PhaseP256_controlled_field_level_vision_experiment.field_validator import (
    validate_diameter,
    validate_legs,
    validate_spacing,
)

from .config import RUNTIME_CONTEXT_KEYS
from .policy import load_insertion_config


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


def numeric_slash_schedule_in_text(text: str) -> bool:
    """True when DXF text itself contains N/M spacing, not C/C truncation."""
    return bool(re.search(r"\d+\s*/\s*\d+", str(text or "")))


def complete_schedule_in_text(text: str, spacings: Sequence[int]) -> bool:
    sp = [int(s) for s in spacings if s]
    if len(sp) < 2:
        return False
    raw = str(text or "")
    if not numeric_slash_schedule_in_text(raw):
        return False
    return all(str(s) in raw for s in sp)


def peer_agreement_count(
    *,
    audit: Dict[str, Any],
    peer_audits: Sequence[Dict[str, Any]],
) -> int:
    vis = audit.get("vision_result") or {}
    dia = vis.get("diameter_mm")
    legs = vis.get("legs")
    spacing = _as_list(vis.get("spacing_mm"))
    n = 0
    cid = str(audit.get("candidate_id") or "")
    for peer in peer_audits:
        if str(peer.get("candidate_id") or "") == cid:
            continue
        if str(peer.get("beam_id")) != str(audit.get("beam_id")):
            continue
        pvis = peer.get("vision_result") or {}
        if pvis.get("diameter_mm") != dia:
            continue
        if pvis.get("legs") != legs:
            continue
        if _as_list(pvis.get("spacing_mm")) != spacing:
            continue
        n += 1
    return n


def build_insertion_context(
    *,
    beam: Optional[Dict[str, Any]],
    audit: Dict[str, Any],
    peer_audits: Optional[Sequence[Dict[str, Any]]] = None,
    owned_by_beam: bool = False,
) -> Dict[str, Any]:
    geom = (beam or {}).get("geometry") or {}
    stirrups = [b for b in ((beam or {}).get("stirrups") or []) if isinstance(b, dict)]
    labels = [str(b.get("bar_label") or "") for b in stirrups]
    vis = audit.get("vision_result") or {}
    det = audit.get("deterministic_result") or {}
    text = str(audit.get("annotation_text") or "")
    vis_spacing = _as_list(vis.get("spacing_mm"))
    ctx = {
        "beam_id": str((beam or {}).get("beam_id") or audit.get("beam_id") or ""),
        "span_mm": geom.get("clear_span_mm") or geom.get("span_mm"),
        "stirrup_count": len(stirrups),
        "has_stirrups": len(stirrups) > 0,
        "stirrup_labels": labels,
        "stirrup_quantities": [b.get("quantity") for b in stirrups],
        "stirrup_diameters": [b.get("diameter_mm") for b in stirrups],
        "stirrup_spacings": [
            str(b.get("spacing_pattern") or b.get("spacing_mm") or "") for b in stirrups
        ],
        "zone_truncated_label": any("#Zone_" in lb or "#ZONE_" in lb.upper() for lb in labels),
        "existing_zone": any("/" in str(b.get("spacing_pattern") or "") for b in stirrups)
        or any("#Zone_" in lb for lb in labels),
        "top_main_count": len((beam or {}).get("top_main_bars") or []),
        "bottom_main_count": len((beam or {}).get("bottom_main_bars") or []),
        "side_face_count": len((beam or {}).get("side_face_reinforcement") or []),
        "annotation_text": text,
        "annotation_id": str(audit.get("annotation_id") or ""),
        "candidate_id": str(audit.get("candidate_id") or ""),
        "det_semantic_type": str(det.get("semantic_type") or ""),
        "vis_semantic_type": str(vis.get("semantic_type") or ""),
        "vis_role": str(vis.get("role") or ""),
        "vis_association": str(vis.get("beam_association") or ""),
        "vis_diameter": vis.get("diameter_mm"),
        "vis_legs": vis.get("legs"),
        "vis_spacing": vis_spacing,
        "vis_quantity": vis.get("quantity"),
        "trigger_reason": list(audit.get("shadow_trigger_reason") or []),
        "owned_by_beam": bool(owned_by_beam),
        "peer_agreement_count": peer_agreement_count(audit=audit, peer_audits=peer_audits or []),
        "complete_schedule_in_text": complete_schedule_in_text(text, vis_spacing),
        "numeric_slash_schedule_in_text": numeric_slash_schedule_in_text(text),
    }
    assert_runtime_context(ctx)
    return ctx


def independent_insertion_signals(ctx: Dict[str, Any]) -> Dict[str, bool]:
    """Signals that support inserting a NEW stirrup object. Not field-recovery signals."""
    assoc = str(ctx.get("vis_association") or "")
    return {
        "existing_zone": bool(ctx.get("existing_zone")),
        "corroborating_annotation": int(ctx.get("peer_agreement_count") or 0) >= 1,
        "complete_schedule_in_text": bool(ctx.get("complete_schedule_in_text")),
        "target_beam_association": assoc == "TARGET_BEAM",
    }


def evaluate_insertion_evidence(
    *,
    ctx: Dict[str, Any],
    classification: Dict[str, Any],
    promoted: List[Dict[str, Any]],
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    assert_runtime_context(ctx)
    cfg = cfg or load_insertion_config()
    new_cfg = cfg.get("creates_new_stirrup") if isinstance(cfg.get("creates_new_stirrup"), dict) else {}
    min_signals = int(new_cfg.get("min_independent_signals") or 2)

    vis_dia = ctx.get("vis_diameter")
    vis_legs = ctx.get("vis_legs")
    vis_spacing = ctx.get("vis_spacing") or []
    dia_ok, dia_err = (True, []) if vis_dia is None else validate_diameter(vis_dia)
    legs_ok, legs_err = (True, []) if vis_legs is None else validate_legs(vis_legs)
    sp_ok, sp_err = (True, []) if not vis_spacing else validate_spacing(list(vis_spacing))

    invented_qty = any(
        r.get("field_name") == "quantity" and r.get("promotion_decision") == "CONTROLLED_RECOMPUTE"
        for r in promoted
    )

    det_type = str(ctx.get("det_semantic_type") or "")
    vis_type = str(ctx.get("vis_semantic_type") or "")
    vis_role = str(ctx.get("vis_role") or "")
    semantic_conflict = bool(
        det_type == "STIRRUP"
        and vis_type
        and vis_type not in ("STIRRUP", "", "UNKNOWN")
        and vis_type != det_type
    ) or (vis_role and vis_role not in ("STIRRUP", "", "UNKNOWN") and det_type == "STIRRUP" and vis_role != "STIRRUP")

    assoc = str(ctx.get("vis_association") or "")
    association_conflict = assoc in ("OTHER_BEAM", "UNCERTAIN")

    existing_dias = []
    for d in ctx.get("stirrup_diameters") or []:
        try:
            existing_dias.append(float(d))
        except Exception:
            continue
    vis_d = None
    try:
        vis_d = float(vis_dia) if vis_dia is not None else None
    except Exception:
        vis_d = None
    second_family = bool(
        ctx.get("has_stirrups")
        and vis_d is not None
        and existing_dias
        and all(abs(d - vis_d) >= 0.6 for d in existing_dias)
        and classification.get("new_stirrup_object")
    )

    signals = independent_insertion_signals(ctx)
    signal_count = sum(1 for v in signals.values() if v)
    sufficient = signal_count >= min_signals

    hard: List[str] = []
    if not dia_ok:
        hard.extend(dia_err or ["INVALID_DIAMETER"])
    if not legs_ok:
        hard.extend(legs_err or ["INVALID_LEGS"])
    if not sp_ok:
        hard.extend(sp_err or ["INVALID_SPACING"])
    if invented_qty:
        hard.append("INVENTED_QUANTITY")
    if semantic_conflict:
        hard.append("DETERMINISTIC_SEMANTIC_CONFLICT")
    if association_conflict:
        hard.append("BEAM_ASSOCIATION_CONFLICT")
    if second_family and new_cfg.get("reject_second_stirrup_family", True):
        hard.append("INCOMPATIBLE_EXISTING_STIRRUP")
    if any(r.get("production_write") is True for r in promoted):
        hard.append("PRODUCTION_MUTATION_ATTEMPT")

    return {
        "sufficient": sufficient,
        "signal_count": signal_count,
        "min_independent_signals": min_signals,
        "signals": signals,
        "hard_reasons": hard,
        "diameter_ok": dia_ok,
        "legs_ok": legs_ok,
        "spacing_ok": sp_ok,
        "invented_quantity": invented_qty,
        "semantic_conflict": semantic_conflict,
        "association_conflict": association_conflict,
        "second_stirrup_family": second_family,
    }


__all__ = [
    "assert_runtime_context",
    "build_insertion_context",
    "complete_schedule_in_text",
    "evaluate_insertion_evidence",
    "independent_insertion_signals",
    "numeric_slash_schedule_in_text",
    "peer_agreement_count",
]
