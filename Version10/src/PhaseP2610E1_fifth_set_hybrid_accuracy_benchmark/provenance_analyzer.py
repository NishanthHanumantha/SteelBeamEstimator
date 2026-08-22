"""Provenance coverage. This is coverage, not accuracy."""
from __future__ import annotations

from typing import Any, Dict, List


def _field_source(rec: Any) -> str:
    if isinstance(rec, dict):
        src = str(rec.get("source") or "")
        if rec.get("fallback_used"):
            return "FALLBACK"
        if src == "VISION":
            return "VISION"
        if src == "DETERMINISTIC":
            return "DETERMINISTIC"
        if src == "UNRESOLVED":
            return "UNRESOLVED"
    return "UNRESOLVED"


def analyze(calcs: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {"VISION": 0, "DETERMINISTIC": 0, "FALLBACK": 0, "UNRESOLVED": 0, "WITHHELD": 0}
    beam_kinds = {"HYBRID": 0, "FALLBACK": 0, "DETERMINISTIC": 0}
    withheld = 0
    details = []
    for calc in calcs:
        kind = str(calc.get("provenance_kind") or "FALLBACK")
        beam_kinds[kind] = beam_kinds.get(kind, 0) + 1
        withheld += len(calc.get("withheld_ambiguous") or [])
        hybrid = calc.get("hybrid_semantic") if isinstance(calc.get("hybrid_semantic"), dict) else {}
        for g in hybrid.get("reinforcement_groups") or []:
            recs = {
                "layer": g.get("layer"),
                "role": g.get("role"),
                "bar_count": g.get("bar_count"),
                "diameter": g.get("diameter"),
                "specification": g.get("specification"),
                "support_scope": g.get("support_scope"),
            }
            for name, rec in recs.items():
                src = _field_source(rec)
                counts[src] = counts.get(src, 0) + 1
                if src == "UNRESOLVED":
                    details.append({"beam_id": calc.get("beam_id"), "group_id": g.get("group_id"), "field": name})
            if g.get("origin") == "AMBIGUOUS" or (g.get("provenance") or {}).get("resolution_reason") == "AMBIGUOUS":
                counts["WITHHELD"] += 1
    total = sum(counts[k] for k in ("VISION", "DETERMINISTIC", "FALLBACK", "UNRESOLVED"))
    pct = {k: round(100.0 * v / total, 2) if total else 0.0 for k, v in counts.items()}
    return {
        "label": "PROVENANCE_COVERAGE_NOT_ACCURACY",
        "field_counts": counts,
        "field_percent": pct,
        "beam_kinds": beam_kinds,
        "withheld_groups": withheld,
        "unresolved_samples": details[:50],
        "total_semantic_fields": total,
    }


__all__ = ["analyze"]
