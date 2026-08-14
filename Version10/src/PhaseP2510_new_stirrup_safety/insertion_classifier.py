"""Classify whether Vision recovery would create new stirrup engineering content.

Operates on a deepcopy via the existing P2.5.8 overlay. Does not mutate the
caller-supplied R1.3 document.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Sequence

from PhaseP258_controlled_vision_field_repair.notation_builder import (
    merge_with_deterministic,
    selected_interpretation,
)
from PhaseP258_controlled_vision_field_repair.r13_overlay import apply_repairs
from PhaseP259_beam_safe_arbitration.beam_safety import estimate_si1_piece_count

from .config import CLS_CREATES_NEW, CLS_NO_NEW, CLS_SUPPLEMENT


def _as_list(v: Any) -> List[int]:
    out: List[int] = []
    for x in v or []:
        try:
            out.append(int(round(float(x))))
        except Exception:
            continue
    return out


def _stirrups(beam: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not beam:
        return []
    return [b for b in (beam.get("stirrups") or []) if isinstance(b, dict)]


def _spacing_of(bar: Dict[str, Any]) -> List[int]:
    pattern = str(bar.get("spacing_pattern") or "")
    if pattern and "/" in pattern:
        return _as_list(pattern.split("/"))
    raw = bar.get("spacing_mm")
    if isinstance(raw, list):
        return _as_list(raw)
    if raw is not None:
        return _as_list([raw])
    return []


def _zone_count(spacings: Sequence[int]) -> int:
    return len([s for s in spacings if s])


def _fields_equivalent(before: Dict[str, Any], filled: Dict[str, Any]) -> bool:
    b_dia = before.get("diameter_mm")
    f_dia = filled.get("diameter_mm")
    try:
        dia_same = b_dia is not None and f_dia is not None and abs(float(b_dia) - float(f_dia)) < 0.6
    except Exception:
        dia_same = b_dia == f_dia
    b_sp = _spacing_of(before)
    f_sp = _as_list(filled.get("spacing_mm"))
    return bool(dia_same and b_sp and f_sp and b_sp == f_sp)


def snapshot_stirrup_state(beam: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    bars = _stirrups(beam)
    spacings = [_spacing_of(b) for b in bars]
    labels = [str(b.get("bar_label") or "") for b in bars]
    return {
        "count": len(bars),
        "labels": labels,
        "diameters": [b.get("diameter_mm") for b in bars],
        "spacings": spacings,
        "quantities": [b.get("quantity") for b in bars],
        "roles": [str(b.get("semantic_role") or b.get("piece_type") or "") for b in bars],
        "has_zone": any(_zone_count(s) > 1 for s in spacings)
        or any("#Zone_" in lb or "#ZONE_" in lb.upper() for lb in labels),
        "uniform": all(_zone_count(s) <= 1 for s in spacings) if spacings else True,
    }


def classify_insertion(
    *,
    r13_doc: Dict[str, Any],
    audits: List[Dict[str, Any]],
    promoted: List[Dict[str, Any]],
    beam_id: str,
    span_mm: Optional[float] = None,
) -> Dict[str, Any]:
    """Compare deterministic beam BEFORE overlay vs hypothetical AFTER overlay."""
    original = copy.deepcopy(r13_doc)
    before_models = {
        m.get("beam_id"): m for m in (original.get("models") or []) if isinstance(m, dict)
    }
    before_beam = before_models.get(beam_id)
    before_state = snapshot_stirrup_state(before_beam)

    beam_promoted = [r for r in promoted if str(r.get("beam_id")) == str(beam_id)]
    beam_audits = [a for a in audits if str(a.get("beam_id")) == str(beam_id)]
    patched, provenance = apply_repairs(
        r13_doc=original, audits=beam_audits, promoted=beam_promoted
    )
    after_models = {
        m.get("beam_id"): m for m in (patched.get("models") or []) if isinstance(m, dict)
    }
    after_beam = after_models.get(beam_id)
    after_state = snapshot_stirrup_state(after_beam)

    actions = [p.get("action") for p in provenance if p.get("beam_id") == beam_id]
    inserted = "INSERTED_SHADOW_STIRRUP" in actions
    patched_existing = "PATCHED_EXISTING_STIRRUP" in actions

    filled: Dict[str, Any] = {}
    if beam_audits and beam_promoted:
        interp = selected_interpretation(
            beam_promoted, fallback_text=str(beam_audits[0].get("annotation_text") or "")
        )
        det = beam_audits[0].get("deterministic_result") or {}
        _, filled = merge_with_deterministic(interp, det)

    vis_spacing = _as_list(filled.get("spacing_mm"))
    before_spacings = [s for row in before_state["spacings"] for s in row]
    after_spacings = [s for row in after_state["spacings"] for s in row]
    before_zone_n = max((_zone_count(s) for s in before_state["spacings"]), default=0)
    after_zone_n = max((_zone_count(s) for s in after_state["spacings"]), default=0)
    new_zone = after_zone_n > 1 and before_zone_n <= 1
    new_stirrup_object = inserted or after_state["count"] > before_state["count"]

    before_pieces = estimate_si1_piece_count(span_mm, before_spacings or vis_spacing[:0])
    if before_state["count"] == 0:
        before_pieces = 0
    after_pieces = estimate_si1_piece_count(span_mm, after_spacings or vis_spacing)
    new_piece = bool(
        after_pieces is not None
        and (before_pieces or 0) < after_pieces
        and (new_stirrup_object or new_zone or after_zone_n > before_zone_n)
    )
    new_steel = bool(new_stirrup_object or new_piece or (after_state["count"] > 0 and before_state["count"] == 0))

    existing_stirrup_match = before_state["count"] > 0 and patched_existing and not inserted
    existing_zone_match = bool(before_state["has_zone"]) and after_zone_n > 1
    existing_semantic_match = "STIRRUP" in (before_state["roles"] or []) or before_state["count"] > 0

    reason_codes: List[str] = []
    if inserted or new_stirrup_object:
        classification = CLS_CREATES_NEW
        reason_codes.append("OVERLAY_INSERTS_STIRRUP_OBJECT")
    elif patched_existing and before_state["count"] > 0:
        matched_bar = _stirrups(before_beam)[0] if _stirrups(before_beam) else {}
        if filled and _fields_equivalent(matched_bar, filled):
            classification = CLS_NO_NEW
            reason_codes.append("EXISTING_STIRRUP_ALREADY_EQUIVALENT")
        else:
            classification = CLS_SUPPLEMENT
            reason_codes.append("PATCHES_EXISTING_STIRRUP_FIELDS")
    else:
        classification = CLS_NO_NEW
        reason_codes.append("NO_OVERLAY_STIRRUP_CHANGE")

    if new_zone:
        reason_codes.append("SPACING_INTRODUCES_NEW_ZONE")
    if new_piece:
        reason_codes.append("SI1_PIECE_COUNT_INCREASES")
    if new_steel:
        reason_codes.append("NEW_STIRRUP_STEEL_WOULD_BE_CREATED")

    return {
        "beam_id": beam_id,
        "classification": classification,
        "new_stirrup_object": bool(new_stirrup_object),
        "new_zone": bool(new_zone),
        "new_piece": bool(new_piece),
        "new_steel": bool(new_steel),
        "existing_stirrup_match": bool(existing_stirrup_match),
        "existing_zone_match": bool(existing_zone_match),
        "existing_semantic_match": bool(existing_semantic_match),
        "reason_codes": reason_codes,
        "evidence": {
            "overlay_actions": actions,
            "before": before_state,
            "after": after_state,
            "filled": filled,
            "before_piece_estimate": before_pieces,
            "after_piece_estimate": after_pieces,
        },
    }


__all__ = ["classify_insertion", "snapshot_stirrup_state"]
