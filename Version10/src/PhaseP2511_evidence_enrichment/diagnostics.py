"""P2.5.11 diagnostics. Evaluation fixtures live here, not in the runtime gate."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PhaseP2510_new_stirrup_safety.diagnostics import (
    UNKNOWN_ONLY_IMPROVEMENT_FIXTURES,
    UNKNOWN_ONLY_WORSENING_FIXTURES,
)

P2510_ALLOW_FIXTURES = ("B128", "B168", "B74", "B76")
P2510_HOLD_RECOVERY_FIXTURES = (
    "B129",
    "B130",
    "B137",
    "B142",
    "B181",
    "B41",
    "B43",
    "B46",
    "B47",
    "B58",
    "B59",
    "B62",
    "B63",
    "B71",
    "B81",
)


def _steel_map(books: Dict[str, Any], key: str) -> Dict[str, float]:
    payload = books.get(key) or {}
    out: Dict[str, float] = {}
    for b in payload.get("beams") or []:
        out[str(b.get("beam_id"))] = float(b.get("steel_kg") or 0.0)
    return out


def _effect(det: float, shadow: float, est: float) -> str:
    b_err = abs(det - est)
    s_err = abs(shadow - est)
    if s_err + 0.05 < b_err:
        return "IMPROVED"
    if b_err + 0.05 < s_err:
        return "WORSENED"
    return "UNCHANGED"


def build_case_diagnostics(
    *,
    decisions: List[Dict[str, Any]],
    books: Dict[str, Any],
    candidates: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    det = _steel_map(books, "baseline")
    shadow = _steel_map(books, "shadow")
    est = _steel_map(books, "estimator")
    cand_by: Dict[str, List[Dict[str, Any]]] = {}
    for c in candidates or []:
        if c.get("promotion_decision") == "CONTROLLED_RECOMPUTE":
            cand_by.setdefault(str(c.get("beam_id")), []).append(c)
    rows: List[Dict[str, Any]] = []
    for d in decisions:
        bid = str(d.get("beam_id") or "")
        resolved = d.get("resolved") or {}
        ins = d.get("insertion") or {}
        filled = (ins.get("evidence") or {}).get("filled") or {}
        recs = cand_by.get(bid) or []
        det_kg = det.get(bid, 0.0)
        s_kg = shadow.get(bid, det_kg)
        e_kg = est.get(bid, 0.0)
        rows.append(
            {
                "beam_id": bid,
                "p259_classification": "OCR_STIRRUP_RECOVERY" if recs else "NONE",
                "p2510_decision": d.get("p2510_decision"),
                "p2511_decision": d.get("decision"),
                "notation": filled.get("bar_label") or (recs[0].get("annotation_text") if recs else None),
                "diameter": filled.get("diameter_mm"),
                "legs": filled.get("legs"),
                "spacing": filled.get("spacing_mm"),
                "beam_association": (resolved.get("target_association")),
                "annotation_quality": resolved.get("annotation_quality"),
                "engineering_plausibility": resolved.get("engineering_plausibility"),
                "spatial_evidence": resolved.get("spatial_evidence"),
                "contextual_evidence": resolved.get("contextual_evidence"),
                "complete_schedule": resolved.get("complete_schedule"),
                "evidence_strength": d.get("evidence_strength"),
                "reason_codes": d.get("reason_codes") or [],
                "production_write": False,
                "steel_before": round(det_kg, 3),
                "steel_after": round(s_kg, 3),
                "steel_delta": round(s_kg - det_kg, 3),
                "shadow_accuracy_effect": _effect(det_kg, s_kg, e_kg),
            }
        )
    return rows


def fixture_outcomes(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by = {r["beam_id"]: r for r in rows}

    def _dec(ids) -> Dict[str, Any]:
        return {i: (by[i].get("p2511_decision") if i in by else None) for i in ids}

    worse = _dec(UNKNOWN_ONLY_WORSENING_FIXTURES)
    allow4 = _dec(P2510_ALLOW_FIXTURES)
    held15 = _dec(P2510_HOLD_RECOVERY_FIXTURES)
    worse_allowed = [i for i, d in worse.items() if d == "ALLOW"]
    return {
        "worsening_fixture_decisions": worse,
        "p2510_allow_fixture_decisions": allow4,
        "hold_recovery_fixture_decisions": held15,
        "known_worsenings_allowed": worse_allowed,
        "known_worsenings_blocked": len(worse_allowed) == 0 and all(v == "HOLD" for v in worse.values() if v),
        "p2510_allows_preserved": all(v == "ALLOW" for v in allow4.values() if v),
    }


__all__ = [
    "P2510_ALLOW_FIXTURES",
    "P2510_HOLD_RECOVERY_FIXTURES",
    "UNKNOWN_ONLY_IMPROVEMENT_FIXTURES",
    "UNKNOWN_ONLY_WORSENING_FIXTURES",
    "build_case_diagnostics",
    "fixture_outcomes",
]
