"""Production-available beam-safety signals. MUST NOT read estimator or GT steel."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence

from .config import (
    REASON_ARB_ACCEPTED,
    REASON_EXISTING_STIRRUP,
    REASON_PARTIAL_EXPANDS,
    REASON_PARTIAL_LOW_CONF,
    REASON_PARTIAL_PIECE_COUNT,
    REASON_PARTIAL_SEGMENTATION,
    REASON_ZONE_TRUNCATED,
)
from .policy import load_arbitration_config


def assert_no_ground_truth(context: Optional[Dict[str, Any]]) -> None:
    if not context:
        return
    for k in context.keys():
        lk = str(k).lower()
        if any(f in lk for f in ("estimator", "ground_truth", "gt_steel", "benchmark_answer")):
            raise ValueError(f"GT leakage: context key {k!r} is forbidden in runtime arbitration")


def build_beam_contexts(r13_doc: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """R1.3-only context. No estimator workbook."""
    out: Dict[str, Dict[str, Any]] = {}
    for model in r13_doc.get("models") or []:
        if not isinstance(model, dict):
            continue
        bid = str(model.get("beam_id") or "")
        geom = model.get("geometry") or {}
        stirrups = [b for b in (model.get("stirrups") or []) if isinstance(b, dict)]
        labels = [str(b.get("bar_label") or "") for b in stirrups]
        out[bid] = {
            "beam_id": bid,
            "span_mm": geom.get("clear_span_mm") or geom.get("span_mm"),
            "stirrup_count": len(stirrups),
            "has_stirrups": len(stirrups) > 0,
            "stirrup_labels": labels,
            "stirrup_quantities": [b.get("quantity") for b in stirrups],
            "zone_truncated_label": any("#Zone_" in lb or "#ZONE_" in lb.upper() for lb in labels),
            "top_main_count": len(model.get("top_main_bars") or []),
            "bottom_main_count": len(model.get("bottom_main_bars") or []),
        }
        assert_no_ground_truth(out[bid])
    return out


def _as_list(v: Any) -> List[int]:
    out: List[int] = []
    for x in v or []:
        try:
            out.append(int(round(float(x))))
        except Exception:
            continue
    return out


def estimate_si1_piece_count(span_mm: Optional[float], spacings: Sequence[int]) -> Optional[int]:
    """
    Identity of Phase SI.1 StirrupQuantityEngine published formulas.
    Not a second steel calculator — arbitration pre-check only.
    """
    if span_mm is None:
        return None
    try:
        span = float(span_mm)
    except Exception:
        return None
    sp = [int(s) for s in spacings if s]
    if span <= 0 or not sp or any(s <= 0 for s in sp):
        return None
    if len(sp) == 1:
        return int(math.floor(span / sp[0]) + 1)
    n = len(sp)
    zone = span / n
    if n >= 3 and sp[0] == sp[-1]:
        support = int(math.floor((2.0 * zone) / sp[0]) + 1)
        mid_len = zone * (n - 2)
        mid_s = sp[1] if n == 3 else min(sp[1:-1])
        mid = int(math.floor(mid_len / mid_s)) if mid_s > 0 else 0
        return support + mid
    total = 0
    for i, s in enumerate(sp):
        length = zone
        if i == 0 or i == n - 1:
            total += int(math.floor(length / s) + (1 if i == 0 else 0))
        else:
            total += int(math.floor(length / s))
    return total


def spacing_expands(det_val: Any, vis_val: Any) -> bool:
    d = _as_list(det_val)
    v = _as_list(vis_val)
    return bool(d) and bool(v) and len(v) > len(d)


def segmentation_changes(det_val: Any, vis_val: Any) -> bool:
    d = _as_list(det_val)
    v = _as_list(vis_val)
    return (len(d) <= 1) and (len(v) > 1)


def evaluate_conservative_partial(
    *,
    field: str,
    det_val: Any,
    vis_val: Any,
    beam_ctx: Optional[Dict[str, Any]],
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Return {accept: bool, reason_codes: [...], signals: {...}}.
    Forbidden to use estimator/GT. Caller must not pass them in beam_ctx.
    """
    assert_no_ground_truth(beam_ctx)
    cfg = cfg or load_arbitration_config()
    partial_cfg = cfg.get("partial") if isinstance(cfg.get("partial"), dict) else {}
    codes: List[str] = []
    span = (beam_ctx or {}).get("span_mm")
    det_n = len(_as_list(det_val)) if field == "spacing" else 0
    vis_n = len(_as_list(vis_val)) if field == "spacing" else 0
    expands = field == "spacing" and spacing_expands(det_val, vis_val)
    seg = field == "spacing" and segmentation_changes(det_val, vis_val)
    det_qty = estimate_si1_piece_count(span, _as_list(det_val)) if field == "spacing" else None
    vis_qty = estimate_si1_piece_count(span, _as_list(vis_val)) if field == "spacing" else None
    qty_up = det_qty is not None and vis_qty is not None and vis_qty > det_qty
    has_stirrups = bool((beam_ctx or {}).get("has_stirrups"))
    truncated = bool((beam_ctx or {}).get("zone_truncated_label"))
    span_missing = field == "spacing" and (span is None or float(span or 0) <= 0)

    if partial_cfg.get("hold_if_spacing_value_count_increases", True) and expands:
        codes.append(REASON_PARTIAL_EXPANDS)
    if partial_cfg.get("hold_if_si1_segmentation_changes", True) and seg:
        codes.append(REASON_PARTIAL_SEGMENTATION)
    if partial_cfg.get("hold_if_estimated_piece_count_increases", True) and qty_up:
        codes.append(REASON_PARTIAL_PIECE_COUNT)
    if partial_cfg.get("hold_if_beam_already_has_stirrups", True) and has_stirrups and field == "spacing":
        codes.append(REASON_EXISTING_STIRRUP)
    if partial_cfg.get("hold_if_existing_stirrup_label_is_zone_truncated", True) and truncated:
        codes.append(REASON_ZONE_TRUNCATED)
    if partial_cfg.get("hold_if_span_unavailable", True) and span_missing:
        codes.append(REASON_PARTIAL_LOW_CONF)

    accept = len(codes) == 0
    if accept:
        codes.append(REASON_ARB_ACCEPTED)
    return {
        "accept": accept,
        "reason_codes": codes,
        "signals": {
            "field": field,
            "det_value_count": det_n,
            "vis_value_count": vis_n,
            "expands_spacing": expands,
            "si1_segmentation_changes": seg,
            "estimated_qty_deterministic": det_qty,
            "estimated_qty_vision": vis_qty,
            "estimated_qty_increases": qty_up,
            "has_stirrups": has_stirrups,
            "zone_truncated_label": truncated,
            "span_mm": span,
            "span_missing": span_missing,
        },
    }


__all__ = [
    "assert_no_ground_truth",
    "build_beam_contexts",
    "estimate_si1_piece_count",
    "evaluate_conservative_partial",
    "segmentation_changes",
    "spacing_expands",
]
