"""Observational relative length / span evidence. Never overrides role."""
from __future__ import annotations

from typing import Any, Dict, List


def _span_from_scope(scope: str) -> str:
    s = str(scope or "UNKNOWN").upper()
    if s == "FULL_SPAN":
        return "FULL_SPAN"
    if s == "LEFT_SUPPORT":
        return "PARTIAL_LEFT"
    if s == "RIGHT_SUPPORT":
        return "PARTIAL_RIGHT"
    if s in ("BOTH_SUPPORTS", "PARTIAL_SUPPORT"):
        return "PARTIAL_SUPPORT"
    return "UNKNOWN"


def attach_length_evidence(groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for g in groups or []:
        row = dict(g)
        length = str(row.get("relative_length_evidence") or "UNKNOWN").upper()
        span = str(row.get("span_relationship") or "UNKNOWN").upper()
        if span == "UNKNOWN":
            span = _span_from_scope(row.get("support_scope") or "")
        if length not in ("LONGER", "SHORTER", "SIMILAR", "UNKNOWN"):
            length = "UNKNOWN"
        row["relative_length_evidence"] = length
        row["span_relationship"] = span if span else "UNKNOWN"
        out.append(row)
    return out


def summarize_length_vs_role(groups: List[Dict[str, Any]]) -> Dict[str, Any]:
    usable = 0
    align = 0
    conflict = 0
    insufficient = 0
    for g in groups or []:
        length = str(g.get("relative_length_evidence") or "UNKNOWN").upper()
        role = str(g.get("role_hypothesis") or g.get("role") or "UNKNOWN").upper()
        if length == "UNKNOWN":
            insufficient += 1
            continue
        usable += 1
        if role == "MAIN" and length == "LONGER":
            align += 1
        elif role == "EXTRA" and length == "SHORTER":
            align += 1
        elif role in ("MAIN", "EXTRA") and length in ("LONGER", "SHORTER"):
            conflict += 1
        else:
            insufficient += 1
    return {
        "groups_with_usable_relative_span": usable,
        "role_hypothesis_aligns": align,
        "role_hypothesis_conflicts": conflict,
        "evidence_insufficient": insufficient,
        "note": "Observational only. Relative length does not override role_hypothesis.",
    }


__all__ = ["attach_length_evidence", "summarize_length_vs_role"]
