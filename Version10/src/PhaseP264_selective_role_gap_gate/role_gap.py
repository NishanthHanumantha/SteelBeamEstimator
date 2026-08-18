"""
Selective ROLE_COVERAGE_GAP evaluator.

Production-only. Does not use GT, estimator, steel, sampling labels, or Vision output.
Does not guess TOP vs BOTTOM from annotation text.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PhaseP26_vision_candidate_recovery.deterministic_comparator import flatten_r13
from PhaseP263_longitudinal_aware_gate.longitudinal_coverage import (
    parse_longitudinal_annotation,
)

from .config import COVER_LAYER, ROLE_GAP_EXPLAINED, ROLE_GAP_NA, ROLE_GAP_REQUIRED


def _is_extra(bar: Dict[str, Any]) -> bool:
    bid = str(bar.get("bar_id") or "").upper()
    label = str(bar.get("bar_label") or "")
    return "EXTRA" in bid or "#" in label


def _spec(row: Dict[str, Any]) -> Tuple[int, int]:
    qty = int(row.get("quantity") or 1)
    dia = int(row["diameter_mm"])
    return qty, dia


def evaluate_selective_role_gap(
    *,
    rec: Dict[str, Any],
    model: Optional[Dict[str, Any]],
    coverage: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    classification = str((coverage or {}).get("longitudinal_coverage") or "")
    if classification != COVER_LAYER:
        return {
            "role_gap_status": ROLE_GAP_NA,
            "role_gap_reason": "NOT_ROLE_COVERAGE_GAP",
            "unique_accepted_spec_count": 0,
            "accepted_instance_count": 0,
            "populated_layer": None,
            "extra_object_count": 0,
            "accepted_matches_main": False,
            "rejected_matching_populated": False,
        }

    bars = flatten_r13(model)
    top = [b for b in bars if b.get("family") == "TOP"]
    bot = [b for b in bars if b.get("family") == "BOTTOM"]
    if (len(top) > 0) == (len(bot) > 0):
        return {
            "role_gap_status": ROLE_GAP_REQUIRED,
            "role_gap_reason": "LAYER_GAP_INCONSISTENT",
            "unique_accepted_spec_count": 0,
            "accepted_instance_count": 0,
            "populated_layer": None,
            "extra_object_count": 0,
            "accepted_matches_main": False,
            "rejected_matching_populated": False,
        }

    populated = "TOP" if top else "BOTTOM"
    pop_bars = top if populated == "TOP" else bot
    extras = [b for b in pop_bars if _is_extra(b)]
    mains = [b for b in pop_bars if not _is_extra(b)]
    pop_dia = {int(b["diameter_mm"]) for b in pop_bars if b.get("diameter_mm") is not None}
    main_dia = {int(b["diameter_mm"]) for b in mains if b.get("diameter_mm") is not None}
    top_dia = sorted({int(b["diameter_mm"]) for b in top if b.get("diameter_mm") is not None})
    bot_dia = sorted({int(b["diameter_mm"]) for b in bot if b.get("diameter_mm") is not None})
    top_qty = sum(int(b.get("quantity") or 1) for b in top)
    bot_qty = sum(int(b.get("quantity") or 1) for b in bot)

    accepted: List[Dict[str, Any]] = []
    for a in rec.get("accepted_annotations") or []:
        row = parse_longitudinal_annotation(a if isinstance(a, dict) else {"text": str(a)})
        if row is not None:
            accepted.append(row)
    rejected: List[Dict[str, Any]] = []
    for a in rec.get("rejected_annotations") or []:
        row = parse_longitudinal_annotation(a if isinstance(a, dict) else {"text": str(a)})
        if row is not None:
            rejected.append(row)

    acc_specs = [_spec(p) for p in accepted]
    unique_specs = list(dict.fromkeys(acc_specs))
    rej_specs = [_spec(p) for p in rejected]
    rejected_matching = any(s in unique_specs and s[1] in pop_dia for s in rej_specs)
    accepted_matches_main = any(dia in main_dia for _, dia in unique_specs)

    evidence: List[str] = []
    if len(unique_specs) > 1:
        evidence.append("MULTIPLE_ACCEPTED_SPECS")
    if len(acc_specs) > 1 and not rejected_matching:
        evidence.append("REPEATED_ACCEPTED_SPEC_WITHOUT_REJECTED_MATCH")
    if extras:
        evidence.append("POPULATED_LAYER_EXTRAS")
    if rejected_matching:
        evidence.append("REJECTED_SPEC_COVERED_BY_POPULATED_LAYER")
    if accepted_matches_main:
        evidence.append("ACCEPTED_SPEC_MATCHES_MAIN")

    explained = (
        len(unique_specs) == 1
        and accepted_matches_main
        and (
            (len(extras) > 0)
            or rejected_matching
        )
        and not (len(acc_specs) > 1 and not rejected_matching)
    )
    status = ROLE_GAP_EXPLAINED if explained else ROLE_GAP_REQUIRED
    if explained:
        if rejected_matching and extras:
            reason = "MAIN_COVERED_PLUS_EXTRAS_AND_REJECTED_MATCH"
        elif rejected_matching:
            reason = "MAIN_COVERED_PLUS_REJECTED_MATCH"
        else:
            reason = "MAIN_COVERED_PLUS_EXTRAS"
    elif "MULTIPLE_ACCEPTED_SPECS" in evidence:
        reason = "MULTIPLE_ACCEPTED_SPECS"
    elif "REPEATED_ACCEPTED_SPEC_WITHOUT_REJECTED_MATCH" in evidence:
        reason = "REPEATED_ACCEPTED_WITHOUT_REJECTED_MATCH"
    else:
        reason = "SINGLE_SPEC_NO_EXTRAS_OR_REJECTED_MATCH"

    return {
        "role_gap_status": status,
        "role_gap_reason": reason,
        "role_gap_evidence": evidence,
        "unique_accepted_spec_count": len(unique_specs),
        "accepted_instance_count": len(acc_specs),
        "populated_layer": populated,
        "extra_object_count": len(extras),
        "accepted_matches_main": accepted_matches_main,
        "rejected_matching_populated": rejected_matching,
        "populated_diameters": sorted(pop_dia),
        "main_diameters": sorted(main_dia),
        "top_diameters": top_dia,
        "bottom_diameters": bot_dia,
        "top_quantity": top_qty,
        "bottom_quantity": bot_qty,
        "unknown_annotation_count": sum(1 for p in accepted if str(p.get("role") or "UNKNOWN") == "UNKNOWN"),
        "known_role_annotation_count": sum(1 for p in accepted if str(p.get("role") or "UNKNOWN") in ("TOP", "BOTTOM")),
        "accepted_specs": [{"quantity": q, "diameter_mm": d} for q, d in unique_specs],
    }


__all__ = ["evaluate_selective_role_gap"]
