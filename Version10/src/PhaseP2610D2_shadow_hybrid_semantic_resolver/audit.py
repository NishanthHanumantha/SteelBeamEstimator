"""Conflict, fallback, and matching audits for D.2."""
from __future__ import annotations

from typing import Any, Dict, List

from .config import CONFLICT_FIELDS, REASON_FALLBACK, SRC_DET, SRC_VISION


_FIELD_MAP = {
    "LAYER": "layer",
    "ROLE": "role",
    "BAR_COUNT": "bar_count",
    "DIAMETER": "diameter",
    "SPECIFICATION": "specification",
    "SUPPORT_SCOPE": "support_scope",
}


def collect_conflicts(beam: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    bid = beam.get("beam_id")
    tgt = beam.get("target_identity") or {}
    if tgt.get("conflict_detected"):
        rows.append(_conflict_row(bid, None, "TARGET_IDENTITY", tgt))
    for g in beam.get("reinforcement_groups") or []:
        for field, key in _FIELD_MAP.items():
            rec = g.get(key) or {}
            if rec.get("conflict_detected"):
                rows.append(_conflict_row(bid, g.get("group_id"), field, rec))
    for s in (beam.get("stirrups") or {}).get("items") or []:
        rec = s.get("semantic_identification") or {}
        if rec.get("conflict_detected"):
            rows.append(_conflict_row(bid, None, "STIRRUP_IDENTIFICATION", rec))
    return rows


def _conflict_row(beam_id: Any, group_id: Any, field: str, rec: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "beam_id": beam_id,
        "hybrid_group_reference": group_id,
        "field": field,
        "code": f"{field}_CONFLICT",
        "vision_value": rec.get("vision_value"),
        "deterministic_value": rec.get("deterministic_value"),
        "selected_value": rec.get("value"),
        "selected_source": rec.get("source"),
        "vision_confidence": rec.get("confidence"),
        "reason": rec.get("resolution_reason"),
    }


def collect_fallbacks(beam: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    bid = beam.get("beam_id")
    tgt = beam.get("target_identity") or {}
    if tgt.get("fallback_used"):
        rows.append(_fallback_row(bid, None, "TARGET_IDENTITY", tgt))
    for g in beam.get("reinforcement_groups") or []:
        for field, key in _FIELD_MAP.items():
            rec = g.get(key) or {}
            if rec.get("fallback_used") or rec.get("resolution_reason") == REASON_FALLBACK:
                rows.append(_fallback_row(bid, g.get("group_id"), field, rec))
    for s in (beam.get("stirrups") or {}).get("items") or []:
        rec = s.get("semantic_identification") or {}
        if rec.get("fallback_used") or rec.get("resolution_reason") == REASON_FALLBACK:
            rows.append(_fallback_row(bid, None, "STIRRUP_IDENTIFICATION", rec))
    return rows


def _fallback_row(beam_id: Any, group_id: Any, field: str, rec: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "beam_id": beam_id,
        "hybrid_group_reference": group_id,
        "field": field,
        "reason": rec.get("validation_reason") or rec.get("resolution_reason"),
        "deterministic_value": rec.get("deterministic_value"),
        "vision_value": rec.get("vision_value"),
        "vision_available": rec.get("vision_value") not in (None, "", "UNKNOWN"),
        "vision_confidence": rec.get("confidence"),
        "resolution_reason": rec.get("resolution_reason"),
    }


def collect_matching(beam: Dict[str, Any]) -> Dict[str, Any]:
    gm = beam.get("group_matching") or {}
    return {
        "beam_id": beam.get("beam_id"),
        "matched": gm.get("matched"),
        "vision_only": gm.get("vision_only"),
        "deterministic_only": gm.get("deterministic_only"),
        "ambiguous": gm.get("ambiguous"),
        "possible_duplicates": gm.get("possible_duplicates"),
        "pairs": gm.get("pairs"),
        "ambiguous_records": gm.get("ambiguous_records"),
    }


def provenance_counts(beams: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {SRC_VISION: 0, SRC_DET: 0, "UNRESOLVED": 0}
    total = 0

    def bump(rec: Dict[str, Any]) -> None:
        nonlocal total
        src = rec.get("source") or "UNRESOLVED"
        counts[src] = counts.get(src, 0) + 1
        total += 1

    for beam in beams:
        bump(beam.get("target_identity") or {})
        for g in beam.get("reinforcement_groups") or []:
            for key in _FIELD_MAP.values():
                bump(g.get(key) or {})
        for s in (beam.get("stirrups") or {}).get("items") or []:
            bump(s.get("semantic_identification") or {})
    pct = {k: round(100.0 * v / total, 2) if total else 0.0 for k, v in counts.items()}
    return {"counts": counts, "total_fields": total, "percent": pct}


__all__ = ["collect_conflicts", "collect_fallbacks", "collect_matching", "provenance_counts"]
