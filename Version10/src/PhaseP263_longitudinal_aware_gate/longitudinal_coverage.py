"""
Production-only longitudinal coverage evaluator.

Does not use GT, estimator, steel, difficulty band, or Vision output.
Does not guess TOP vs BOTTOM from annotation text when role is unknown.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from PhaseP26_vision_candidate_recovery.deterministic_comparator import flatten_r13, role_family
from PhaseP251_quantity_intent_schema.config import SEM_STIRRUP
from PhaseP251_quantity_intent_schema.parser import parse_quantity_expression

from .config import (
    COVER_DIA,
    COVER_FULL,
    COVER_LAYER,
    COVER_MISSING,
    COVER_MULTI,
    COVER_NONE,
    COVER_QTY,
    COVER_ROLE,
    COVER_UNASSOC,
    COVER_UNCERTAIN,
)

_ROLE_MAP = {
    "TOP": "TOP",
    "TOP_BAR": "TOP",
    "TOP_MAIN": "TOP",
    "TOP_EXTRA": "TOP",
    "BOTTOM": "BOTTOM",
    "BOTTOM_BAR": "BOTTOM",
    "BOTTOM_MAIN": "BOTTOM",
    "BOTTOM_EXTRA": "BOTTOM",
}


def _qty(v: Any) -> Optional[int]:
    try:
        n = int(round(float(v)))
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _norm(text: str) -> str:
    return "".join(str(text or "").split()).upper().replace("\\X", "")


def _role_from_ann(ann: Dict[str, Any]) -> str:
    raw = str(
        ann.get("semantic_role")
        or ann.get("role")
        or ann.get("role_hint")
        or ""
    ).strip().upper()
    return _ROLE_MAP.get(raw, "UNKNOWN")


def parse_longitudinal_annotation(ann: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    text = str(ann.get("text") or ann.get("raw_text") or "")
    if not text.strip():
        return None
    try:
        parsed = parse_quantity_expression(text)
    except Exception:
        parsed = None
    if parsed is not None and parsed.semantic_hint == SEM_STIRRUP:
        return None
    if parsed is None or parsed.diameter_value_mm is None:
        return None
    dia = int(round(float(parsed.diameter_value_mm)))
    if dia <= 0:
        return None
    qty = parsed.quantity_value
    if qty is None:
        qty = _qty(ann.get("quantity"))
    return {
        "text": text,
        "normalized_text": _norm(text),
        "role": _role_from_ann(ann),
        "diameter_mm": dia,
        "quantity": int(qty) if qty else None,
    }


def _bar_qty(bar: Dict[str, Any]) -> int:
    q = _qty(bar.get("quantity"))
    if q is not None:
        return q
    label = str(bar.get("bar_label") or "").split("#")[0]
    if not label.strip():
        return 1
    try:
        parsed = parse_quantity_expression(label)
    except Exception:
        parsed = None
    if parsed is not None and parsed.quantity_value:
        return int(parsed.quantity_value)
    return 1


def _supply(bars: List[Dict[str, Any]]) -> Tuple[Counter, Counter, int, int]:
    by_role_dia: Counter = Counter()
    by_dia: Counter = Counter()
    top = bot = 0
    for b in bars:
        fam = str(b.get("family") or role_family(b.get("semantic_role")) or "")
        if fam not in ("TOP", "BOTTOM"):
            continue
        dia = b.get("diameter_mm")
        if dia is None:
            continue
        dia_i = int(dia)
        q = _bar_qty(b)
        by_role_dia[(fam, dia_i)] += q
        by_dia[dia_i] += q
        if fam == "TOP":
            top += 1
        else:
            bot += 1
    return by_role_dia, by_dia, top, bot


def evaluate_longitudinal_coverage(
    *,
    rec: Dict[str, Any],
    model: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    bars = flatten_r13(model)
    parsed: List[Dict[str, Any]] = []
    for a in rec.get("accepted_annotations") or []:
        row = parse_longitudinal_annotation(a if isinstance(a, dict) else {"text": str(a)})
        if row is None:
            continue
        parsed.append(row)
    unassoc_long = False
    for a in rec.get("rejected_annotations") or []:
        row = parse_longitudinal_annotation(a if isinstance(a, dict) else {"text": str(a)})
        if row is not None:
            unassoc_long = True
            break

    supply_rd, supply_d, top_n, bot_n = _supply(bars)
    if not parsed:
        cond = [COVER_NONE]
        if unassoc_long:
            cond.append(COVER_UNASSOC)
        return {
            "longitudinal_coverage": COVER_NONE,
            "longitudinal_gap": False,
            "coverage_conditions": cond,
            "long_annotation_unique_count": 0,
            "long_top_object_count": top_n,
            "long_bottom_object_count": bot_n,
            "quantity_shortfall_count": 0,
            "role_conflict_count": 0,
            "diameter_conflict_count": 0,
            "layer_gap": False,
            "per_annotation_coverage": [],
        }

    if top_n == 0 and bot_n == 0:
        classification = COVER_MISSING
        conditions = [COVER_MISSING]
        if unassoc_long:
            conditions.append(COVER_UNASSOC)
        per_ann = [{**p, "coverage": COVER_MISSING} for p in parsed]
        return _pack(classification, True, conditions, parsed, top_n, bot_n, per_ann, True)

    conditions: List[str] = []
    per_ann: List[Dict[str, Any]] = []
    qty_n = role_n = dia_n = 0
    layer_gap = (top_n > 0) != (bot_n > 0)
    unknown_present = any(p.get("role") == "UNKNOWN" for p in parsed)
    if layer_gap and unknown_present:
        conditions.append(COVER_LAYER)
    if unassoc_long:
        conditions.append(COVER_UNASSOC)

    demand_d: Counter = Counter()
    demand_rd: Counter = Counter()
    specs_by_dia: Dict[int, set] = {}
    for p in parsed:
        dia = int(p["diameter_mm"])
        qty = int(p["quantity"] or 1)
        demand_d[dia] += qty
        specs_by_dia.setdefault(dia, set()).add((p["quantity"], dia))
        role = p["role"]
        if role in ("TOP", "BOTTOM"):
            demand_rd[(role, dia)] += qty

    obj_groups_by_dia: Counter = Counter()
    for b in bars:
        fam = str(b.get("family") or "")
        if fam in ("TOP", "BOTTOM") and b.get("diameter_mm") is not None:
            obj_groups_by_dia[int(b["diameter_mm"])] += 1

    for p in parsed:
        dia = int(p["diameter_mm"])
        qty = int(p["quantity"] or 1)
        role = p["role"]
        local = COVER_FULL
        if role in ("TOP", "BOTTOM"):
            have = int(supply_rd.get((role, dia), 0) or 0)
            other = "BOTTOM" if role == "TOP" else "TOP"
            other_have = int(supply_rd.get((other, dia), 0) or 0)
            role_any_dia = sum(v for (r, _), v in supply_rd.items() if r == role)
            if have < qty:
                if have == 0 and other_have > 0:
                    local = COVER_ROLE
                    role_n += 1
                elif have == 0 and role_any_dia > 0:
                    local = COVER_DIA
                    dia_n += 1
                else:
                    local = COVER_QTY
                    qty_n += 1
        else:
            have = int(supply_d.get(dia, 0) or 0)
            if have < qty:
                local = COVER_QTY
                qty_n += 1
            elif layer_gap and unknown_present:
                local = COVER_LAYER
        if local != COVER_FULL:
            conditions.append(local)
        per_ann.append({**p, "coverage": local})

    for dia, specs in specs_by_dia.items():
        if len(specs) > max(1, int(obj_groups_by_dia.get(dia, 0) or 0)) and int(
            demand_d.get(dia, 0) or 0
        ) > int(supply_d.get(dia, 0) or 0):
            conditions.append(COVER_MULTI)

    conditions = list(dict.fromkeys(conditions))
    material = [c for c in conditions if c != COVER_UNASSOC]
    if COVER_MISSING in material:
        classification = COVER_MISSING
    elif COVER_LAYER in material:
        classification = COVER_LAYER
    elif COVER_ROLE in material:
        classification = COVER_ROLE
    elif COVER_DIA in material:
        classification = COVER_DIA
    elif COVER_QTY in material:
        classification = COVER_QTY
    elif COVER_MULTI in material:
        classification = COVER_MULTI
    elif material:
        classification = COVER_UNCERTAIN
    else:
        classification = COVER_FULL
        if COVER_FULL not in conditions:
            conditions.append(COVER_FULL)
    gap = classification not in (COVER_FULL, COVER_NONE, COVER_UNCERTAIN)
    return _pack(classification, gap, conditions, parsed, top_n, bot_n, per_ann, layer_gap)


def _pack(
    classification: str,
    gap: bool,
    conditions: List[str],
    parsed: List[Dict[str, Any]],
    top_n: int,
    bot_n: int,
    per_ann: List[Dict[str, Any]],
    layer_gap: bool,
) -> Dict[str, Any]:
    return {
        "longitudinal_coverage": classification,
        "longitudinal_gap": gap,
        "coverage_conditions": conditions,
        "long_annotation_unique_count": len(parsed),
        "long_top_object_count": top_n,
        "long_bottom_object_count": bot_n,
        "quantity_shortfall_count": sum(1 for p in per_ann if p.get("coverage") == COVER_QTY),
        "role_conflict_count": sum(1 for p in per_ann if p.get("coverage") == COVER_ROLE),
        "diameter_conflict_count": sum(1 for p in per_ann if p.get("coverage") == COVER_DIA),
        "layer_gap": layer_gap,
        "per_annotation_coverage": per_ann,
    }


__all__ = ["evaluate_longitudinal_coverage", "parse_longitudinal_annotation"]
