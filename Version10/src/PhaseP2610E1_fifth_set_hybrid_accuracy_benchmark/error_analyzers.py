"""Separate semantic interpretation errors from engineering calculation errors."""
from __future__ import annotations

from typing import Any, Dict, List


_SEMANTIC_STATUS = {
    "WRONG_ROLE": "WRONG_MAIN_EXTRA_ROLE",
    "WRONG_DIAMETER": "WRONG_DIAMETER",
    "WRONG_QUANTITY": "WRONG_BAR_COUNT",
    "MISSING": "MISSED_REINFORCEMENT_GROUPS",
    "PARTIAL_MATCH": "PARTIAL_SEMANTIC_MATCH",
    "WRONG_SPECIFICATION": "WRONG_SPECIFICATION",
}


def semantic_errors(*, bar_matching: Dict[str, Any], beam_matching: Dict[str, Any], calcs: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {
        "MISSED_BEAMS": len(beam_matching.get("missing_ids") or []),
        "WRONG_TARGET_ASSOCIATION": 0,
        "WRONG_LAYER": 0,
        "WRONG_MAIN_EXTRA_ROLE": 0,
        "WRONG_BAR_COUNT": 0,
        "WRONG_DIAMETER": 0,
        "WRONG_SPECIFICATION": 0,
        "MISSED_REINFORCEMENT_GROUPS": 0,
        "PARTIAL_SEMANTIC_MATCH": 0,
        "SPURIOUS": 0,
        "WITHHELD_AMBIGUITY": 0,
    }
    for r in bar_matching.get("rows") or []:
        st = r.get("status")
        if st == "EXTRA":
            counts["SPURIOUS"] += 1
        elif st in _SEMANTIC_STATUS:
            counts[_SEMANTIC_STATUS[st]] += 1
        if r.get("bar_role") and r.get("model_role") and r.get("bar_role") != r.get("model_role") and st == "WRONG_ROLE":
            pass
    for calc in calcs:
        counts["WITHHELD_AMBIGUITY"] += len(calc.get("withheld_ambiguous") or [])
        hybrid = calc.get("hybrid_semantic") if isinstance(calc.get("hybrid_semantic"), dict) else {}
        target = hybrid.get("target_identity") if isinstance(hybrid.get("target_identity"), dict) else {}
        if target.get("conflict_detected"):
            counts["WRONG_TARGET_ASSOCIATION"] += 1
        for g in hybrid.get("reinforcement_groups") or []:
            recs = g.get("layer") if isinstance(g.get("layer"), dict) else {}
            if recs.get("conflict_detected") and recs.get("source") == "VISION":
                vis = recs.get("vision_value")
                det = recs.get("deterministic_value")
                if vis and det and vis != det:
                    counts["WRONG_LAYER"] += 0  # conflict is not yet a GT error
    ranked = sorted(((k, v) for k, v in counts.items() if v), key=lambda kv: -kv[1])
    return {"kind": "SEMANTIC_INTERPRETATION_ERROR", "counts": counts, "ranked": [{"code": k, "count": v} for k, v in ranked]}


def engineering_errors(*, calcs: List[Dict[str, Any]], bar_matching: Dict[str, Any]) -> Dict[str, Any]:
    counts = {
        "CUT_LENGTH_DERIVED_FALLBACK": 0,
        "CUT_LENGTH_UNAVAILABLE": 0,
        "STIRRUP_ENGINEERING_UNAVAILABLE": 0,
        "PARTIAL_CALCULATION": 0,
        "INCOMPATIBLE": 0,
        "SPACER_ZERO": 0,
    }
    for calc in calcs:
        if calc.get("status") in ("SHADOW_PARTIAL", "SHADOW_INCOMPATIBLE"):
            counts["PARTIAL_CALCULATION"] += 1
        if calc.get("status") == "SHADOW_INCOMPATIBLE":
            counts["INCOMPATIBLE"] += 1
        if (calc.get("stirrups") or {}).get("reason") == "DETERMINISTIC_STIRRUP_UNAVAILABLE":
            counts["STIRRUP_ENGINEERING_UNAVAILABLE"] += 1
        if float(calc.get("spacer_weight_kg") or 0) == 0:
            counts["SPACER_ZERO"] += 1
        for g in calc.get("groups") or []:
            reasons = g.get("reasons") or []
            if "CUT_LENGTH_DERIVED_FROM_DETERMINISTIC_ENGINE" in reasons:
                counts["CUT_LENGTH_DERIVED_FALLBACK"] += 1
            if "CUT_LENGTH_UNAVAILABLE" in reasons:
                counts["CUT_LENGTH_UNAVAILABLE"] += 1
    ranked = sorted(((k, v) for k, v in counts.items() if v), key=lambda kv: -kv[1])
    return {
        "kind": "ENGINEERING_CALCULATION_ERROR",
        "counts": counts,
        "ranked": [{"code": k, "count": v} for k, v in ranked],
        "note": "Engineering counts are calculation-trace based, not GT identity matches.",
    }


def stirrup_errors(*, calcs: List[Dict[str, Any]], bar_matching: Dict[str, Any]) -> Dict[str, Any]:
    ident_conflict = 0
    unavailable = 0
    kg = 0.0
    gt_stirrup_missing = 0
    gt_stirrup_match = 0
    gt_stirrup_wrong = 0
    for calc in calcs:
        st = calc.get("stirrups") or {}
        ident_conflict += len(st.get("conflicts") or [])
        if st.get("reason") == "DETERMINISTIC_STIRRUP_UNAVAILABLE":
            unavailable += 1
        kg += float(st.get("weight_kg") or 0)
    for r in bar_matching.get("rows") or []:
        role = str(r.get("bar_role") or r.get("model_role") or "").upper()
        if "STIRRUP" not in role:
            continue
        st = r.get("status")
        if st == "MATCH":
            gt_stirrup_match += 1
        elif st == "MISSING":
            gt_stirrup_missing += 1
        else:
            gt_stirrup_wrong += 1
    return {
        "semantic_identification_authority": "VISION_PREFERRED",
        "engineering_calculation_authority": "DETERMINISTIC_ENGINEERING",
        "identification_conflicts": ident_conflict,
        "engineering_unavailable_beams": unavailable,
        "hybrid_stirrup_kg": round(kg, 4),
        "gt_match": gt_stirrup_match,
        "gt_missing": gt_stirrup_missing,
        "gt_other_errors": gt_stirrup_wrong,
    }


def spacer_report(*, calcs: List[Dict[str, Any]]) -> Dict[str, Any]:
    kg = 0.0
    beams = 0
    groups = 0
    for calc in calcs:
        w = float(calc.get("spacer_weight_kg") or 0)
        if w > 0:
            beams += 1
        kg += w
        groups += int((calc.get("spacers") or {}).get("group_count") or 0)
    return {
        "authority": "DETERMINISTIC_ONLY",
        "vision_matched": False,
        "weight_kg": round(kg, 4),
        "beams_with_spacers": beams,
        "group_count": groups,
    }


__all__ = ["engineering_errors", "semantic_errors", "spacer_report", "stirrup_errors"]
