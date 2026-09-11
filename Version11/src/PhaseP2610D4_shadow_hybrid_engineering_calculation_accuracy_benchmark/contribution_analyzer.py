"""Vision contribution analysis from provenance and field deltas. No beam-ID explanations."""
from __future__ import annotations

from typing import Any, Dict, List


def _rec(group: Dict[str, Any], field: str) -> Dict[str, Any]:
    sem = group.get("semantic") if isinstance(group.get("semantic"), dict) else {}
    recs = sem.get("field_records") if isinstance(sem.get("field_records"), dict) else {}
    rec = recs.get(field)
    return rec if isinstance(rec, dict) else {}


def analyze_beam(*, hybrid: Dict[str, Any], comparison: Dict[str, Any]) -> Dict[str, Any]:
    codes: List[str] = []
    details: List[Dict[str, Any]] = []
    for g in hybrid.get("groups") or []:
        origin = g.get("origin")
        if origin == "VISION_ONLY_GROUP" and not g.get("ambiguous"):
            codes.append("VISION_GROUP_RECOVERY")
            details.append({"code": "VISION_GROUP_RECOVERY", "group_id": g.get("group_id")})
        if origin == "DETERMINISTIC_ONLY_GROUP":
            codes.append("DETERMINISTIC_ONLY_PRESERVED")
        if g.get("ambiguous") or "CALCULATION_WITHHELD_AMBIGUITY" in (g.get("reasons") or []):
            codes.append("AMBIGUOUS_GROUP_WITHHELD")
            details.append({"code": "AMBIGUOUS_GROUP_WITHHELD", "group_id": g.get("group_id")})
        if g.get("possible_duplicate"):
            codes.append("POSSIBLE_DUPLICATE_UNMERGED")
        for field, code in (
            ("diameter", "VISION_DIAMETER_CORRECTION"),
            ("bar_count", "VISION_BAR_COUNT_CORRECTION"),
            ("layer", "VISION_LAYER_CORRECTION"),
            ("role", "VISION_ROLE_CORRECTION"),
            ("specification", "VISION_SPECIFICATION_CORRECTION"),
        ):
            rec = _rec(g, field)
            vis = rec.get("vision_value")
            det = rec.get("deterministic_value")
            if rec.get("source") == "VISION" and vis not in (None, "") and det not in (None, "") and vis != det:
                codes.append(code)
                details.append({"code": code, "group_id": g.get("group_id"), "vision": vis, "deterministic": det})
        if "EXISTING_DETERMINISTIC_CUT_LENGTH" in (g.get("reasons") or []):
            codes.append("DETERMINISTIC_CUT_LENGTH_CONTRIBUTION")
        if "CUT_LENGTH_DERIVED_FROM_DETERMINISTIC_ENGINE" in (g.get("reasons") or []):
            codes.append("DETERMINISTIC_GEOMETRY_CONTRIBUTION")
    if (hybrid.get("spacer_weight_kg") or 0) > 0:
        codes.append("DETERMINISTIC_SPACER_CONTRIBUTION")
    if (hybrid.get("stirrup_weight_kg") or 0) > 0:
        codes.append("DETERMINISTIC_STIRRUP_ENGINEERING_CONTRIBUTION")
    for c in hybrid.get("stirrups", {}).get("conflicts") or []:
        codes.append("STIRRUP_SEMANTIC_CONFLICT")
        details.append(c)

    h = comparison.get("hybrid_kg")
    d = comparison.get("deterministic_kg")
    delta = None
    if h is not None and d is not None:
        delta = round(float(h) - float(d), 4)
    primary = None
    if "AMBIGUOUS_GROUP_WITHHELD" in codes:
        primary = "AMBIGUOUS_GROUP_WITHHELD"
    elif "VISION_DIAMETER_CORRECTION" in codes:
        primary = "VISION_DIAMETER_CORRECTION"
    elif "VISION_BAR_COUNT_CORRECTION" in codes:
        primary = "VISION_BAR_COUNT_CORRECTION"
    elif "VISION_GROUP_RECOVERY" in codes:
        primary = "VISION_GROUP_RECOVERY"
    elif "VISION_ROLE_CORRECTION" in codes:
        primary = "VISION_ROLE_CORRECTION"
    elif delta not in (None, 0):
        primary = "HYBRID_DETERMINISTIC_WEIGHT_DELTA"
    outcome = "UNCHANGED"
    if comparison.get("winner") == "HYBRID":
        outcome = "HYBRID_IMPROVEMENT"
    elif comparison.get("winner") == "DETERMINISTIC":
        outcome = "HYBRID_REGRESSION"
    elif comparison.get("winner") == "TIE":
        outcome = "TIE"
    elif comparison.get("winner") == "NO_BENCHMARK_TRUTH":
        outcome = "NO_BENCHMARK_TRUTH"
    return {
        "beam_id": hybrid.get("beam_id"),
        "codes": sorted(set(codes)),
        "details": details,
        "hybrid_minus_deterministic_kg": delta,
        "primary_cause": primary,
        "outcome": outcome,
        "winner": comparison.get("winner"),
    }


def summarize(analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    outcomes: Dict[str, int] = {}
    for a in analyses:
        for c in a.get("codes") or []:
            counts[c] = counts.get(c, 0) + 1
        o = a.get("outcome") or "UNCHANGED"
        outcomes[o] = outcomes.get(o, 0) + 1
    return {
        "code_counts": counts,
        "outcomes": outcomes,
        "improvements": outcomes.get("HYBRID_IMPROVEMENT", 0),
        "regressions": outcomes.get("HYBRID_REGRESSION", 0),
        "ambiguous_withheld_beams": sum(1 for a in analyses if "AMBIGUOUS_GROUP_WITHHELD" in (a.get("codes") or [])),
    }


__all__ = ["analyze_beam", "summarize"]
