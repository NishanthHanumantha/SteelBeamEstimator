"""Structural hybrid metrics. Not accuracy."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .audit import provenance_counts
from .config import CONFLICT_FIELDS, SRC_DET, SRC_UNRESOLVED, SRC_VISION


_FIELD_KEYS = {
    "TARGET_IDENTITY": ("target",),
    "LAYER": ("group", "layer"),
    "ROLE": ("group", "role"),
    "BAR_COUNT": ("group", "bar_count"),
    "DIAMETER": ("group", "diameter"),
    "SPECIFICATION": ("group", "specification"),
    "SUPPORT_SCOPE": ("group", "support_scope"),
    "STIRRUP_IDENTIFICATION": ("stirrup",),
}


def field_resolution(beams: List[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Counter] = {f: Counter() for f in _FIELD_KEYS}

    def bump(field: str, rec: Dict[str, Any]) -> None:
        src = rec.get("source")
        if src == SRC_VISION:
            out[field]["vision_accepted"] += 1
        elif rec.get("fallback_used") or rec.get("resolution_reason") == "DETERMINISTIC_FALLBACK":
            out[field]["deterministic_fallback"] += 1
        elif src == SRC_DET:
            out[field]["deterministic_authority_or_only"] += 1
        else:
            out[field]["unresolved"] += 1
        if rec.get("conflict_detected"):
            out[field]["conflicts_recorded"] += 1

    for beam in beams:
        bump("TARGET_IDENTITY", beam.get("target_identity") or {})
        for g in beam.get("reinforcement_groups") or []:
            bump("LAYER", g.get("layer") or {})
            bump("ROLE", g.get("role") or {})
            bump("BAR_COUNT", g.get("bar_count") or {})
            bump("DIAMETER", g.get("diameter") or {})
            bump("SPECIFICATION", g.get("specification") or {})
            bump("SUPPORT_SCOPE", g.get("support_scope") or {})
        for s in (beam.get("stirrups") or {}).get("items") or []:
            bump("STIRRUP_IDENTIFICATION", s.get("semantic_identification") or {})
    return {k: dict(v) for k, v in out.items()}


def group_counts(beams: List[Dict[str, Any]]) -> Dict[str, int]:
    matched = vision_only = det_only = ambiguous = dups = 0
    for beam in beams:
        gm = beam.get("group_matching") or {}
        matched += int(gm.get("matched") or 0)
        vision_only += int(gm.get("vision_only") or 0)
        det_only += int(gm.get("deterministic_only") or 0)
        ambiguous += int(gm.get("ambiguous") or 0)
        dups += len(gm.get("possible_duplicates") or [])
    return {
        "matched_groups": matched,
        "vision_only_groups": vision_only,
        "deterministic_only_groups": det_only,
        "ambiguous_groups": ambiguous,
        "possible_duplicates": dups,
    }


def engineering_metrics(beams: List[Dict[str, Any]]) -> Dict[str, int]:
    retained = unavailable = 0
    for beam in beams:
        for g in beam.get("reinforcement_groups") or []:
            eng = g.get("deterministic_engineering") or {}
            if eng.get("source") == SRC_DET:
                retained += 1
            cut = eng.get("cut_length_reference")
            if cut in ("UNAVAILABLE", None, "UNRESOLVED"):
                unavailable += 1
        spacers = beam.get("spacers") or {}
        if spacers.get("source") == SRC_DET:
            retained += 1
    return {
        "deterministic_authority_retained": retained,
        "unavailable_cut_length_references": unavailable,
    }


def stirrup_metrics(beams: List[Dict[str, Any]]) -> Dict[str, int]:
    vis = eng = conflicts = 0
    for beam in beams:
        for s in (beam.get("stirrups") or {}).get("items") or []:
            ident = s.get("semantic_identification") or {}
            if ident.get("source") == SRC_VISION:
                vis += 1
            eng_ref = s.get("engineering_calculation_reference") or {}
            if eng_ref.get("source") == SRC_DET:
                eng += 1
            if ident.get("conflict_detected"):
                conflicts += 1
    return {
        "vision_semantic_identification_accepted": vis,
        "deterministic_engineering_references_retained": eng,
        "conflicts_recorded": conflicts,
    }


def build_metrics(beams: List[Dict[str, Any]]) -> Dict[str, Any]:
    resolved = sum(1 for b in beams if b.get("successfully_resolved"))
    return {
        "population": {
            "total_beams": len(beams),
            "successfully_resolved_beams": resolved,
            "unresolved_beams": len(beams) - resolved,
        },
        "groups": group_counts(beams),
        "field_resolution": field_resolution(beams),
        "engineering_fields": engineering_metrics(beams),
        "stirrups": stirrup_metrics(beams),
        "provenance": provenance_counts(beams),
        "note": "Structural metrics only. Not accuracy.",
    }


__all__ = ["build_metrics"]
