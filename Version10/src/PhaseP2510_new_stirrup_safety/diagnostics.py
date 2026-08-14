"""Beam-level P2.5.10 diagnostics. Evaluation fixtures live here, not in the runtime gate."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

# Evaluation-only diagnostic fixtures. NEVER imported by runtime gate modules.
UNKNOWN_ONLY_WORSENING_FIXTURES = (
    "B139",
    "B141",
    "B144",
    "B147",
    "B16",
    "B17",
    "B178",
    "B80",
    "B82",
    "B86",
)
UNKNOWN_ONLY_IMPROVEMENT_FIXTURES = (
    "B128",
    "B129",
    "B130",
    "B46",
    "B58",
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


def build_beam_diagnostics(
    *,
    decisions: List[Dict[str, Any]],
    books: Dict[str, Any],
    unknown_books: Optional[Dict[str, Any]] = None,
    candidates: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    det = _steel_map(books, "baseline")
    gated = _steel_map(books, "shadow")
    est = _steel_map(books, "estimator")
    unknown = _steel_map(unknown_books or {}, "shadow") if unknown_books else {}
    cand_by: Dict[str, List[Dict[str, Any]]] = {}
    for c in candidates or []:
        if c.get("promotion_decision") == "CONTROLLED_RECOMPUTE":
            cand_by.setdefault(str(c.get("beam_id")), []).append(c)

    rows: List[Dict[str, Any]] = []
    for d in decisions:
        bid = str(d.get("beam_id") or "")
        ins = d.get("insertion") or {}
        before = (ins.get("evidence") or {}).get("before") or {}
        after = (ins.get("evidence") or {}).get("after") or {}
        filled = (ins.get("evidence") or {}).get("filled") or {}
        ev = d.get("evidence") or {}
        recs = cand_by.get(bid) or []
        det_kg = det.get(bid, 0.0)
        g_kg = gated.get(bid, det_kg)
        e_kg = est.get(bid, 0.0)
        u_kg = unknown.get(bid)
        rows.append(
            {
                "beam_id": bid,
                "p259_classification": "OCR_STIRRUP_RECOVERY" if recs else "NONE",
                "insertion_classification": d.get("classification"),
                "gate_decision": d.get("decision"),
                "reason_codes": d.get("reason_codes") or [],
                "deterministic_stirrup_state": before,
                "vision_recovery": filled,
                "existing_zone": bool(ins.get("existing_zone_match") or before.get("has_zone")),
                "new_zone": bool(ins.get("new_zone")),
                "existing_piece": bool(before.get("count")),
                "new_piece": bool(ins.get("new_piece")),
                "steel_before": round(det_kg, 3),
                "steel_after": round(g_kg, 3),
                "steel_delta": round(g_kg - det_kg, 3),
                "unknown_only_steel": None if u_kg is None else round(u_kg, 3),
                "production_evidence_summary": ev.get("signals") or {},
                "independent_signal_count": ev.get("signal_count"),
                "shadow_accuracy_effect": _effect(det_kg, g_kg, e_kg),
                "overlay_after": after,
                "vision_fields": [
                    {
                        "field_name": c.get("field_name"),
                        "vision_value": c.get("vision_value"),
                        "deterministic_status": c.get("deterministic_status"),
                    }
                    for c in recs
                ],
            }
        )
    return rows


def fixture_outcomes(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by = {r["beam_id"]: r for r in rows}

    def _subset(ids: tuple) -> List[Dict[str, Any]]:
        return [by[i] for i in ids if i in by]

    worse = _subset(UNKNOWN_ONLY_WORSENING_FIXTURES)
    good = _subset(UNKNOWN_ONLY_IMPROVEMENT_FIXTURES)
    return {
        "worsening_fixtures": worse,
        "improvement_fixtures": good,
        "worsening_fixture_decisions": {r["beam_id"]: r.get("gate_decision") for r in worse},
        "improvement_fixture_decisions": {r["beam_id"]: r.get("gate_decision") for r in good},
        "missing_worsening_fixtures": [i for i in UNKNOWN_ONLY_WORSENING_FIXTURES if i not in by],
        "missing_improvement_fixtures": [i for i in UNKNOWN_ONLY_IMPROVEMENT_FIXTURES if i not in by],
    }


def affected_beam_ids(decisions: List[Dict[str, Any]]) -> Set[str]:
    return {str(d.get("beam_id")) for d in decisions if d.get("classification")}


__all__ = [
    "UNKNOWN_ONLY_IMPROVEMENT_FIXTURES",
    "UNKNOWN_ONLY_WORSENING_FIXTURES",
    "build_beam_diagnostics",
    "fixture_outcomes",
]
