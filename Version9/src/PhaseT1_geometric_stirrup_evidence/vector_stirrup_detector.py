"""
Vector-space stirrup detector — elevation tick trains + section rectangles.
MODEL_VERSION: 9.3.0
"""
from __future__ import annotations

import math
import statistics
from typing import Any, Dict, List, Optional, Sequence, Tuple

MODEL_VERSION = "9.3.0"


def _cv(vals: Sequence[float]) -> float:
    if len(vals) < 2:
        return 0.0
    mean = statistics.mean(vals)
    if mean <= 1e-9:
        return 999.0
    return statistics.pstdev(vals) / mean


def _line_endpoints(entity) -> Optional[Tuple[float, float, float, float]]:
    try:
        s = entity.dxf.start
        e = entity.dxf.end
        return float(s.x), float(s.y), float(e.x), float(e.y)
    except Exception:
        return None


def _is_short_vertical(
    x1: float, y1: float, x2: float, y2: float,
    *,
    max_len: float = 900.0,
    min_len: float = 15.0,
    max_dx_ratio: float = 0.45,
) -> bool:
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    length = math.hypot(dx, dy)
    if length < min_len or length > max_len:
        return False
    if dy < 1e-6:
        return False
    return (dx / dy) <= max_dx_ratio


def detect_elevation_ticks(
    msp,
    beam_bbox: Tuple[float, float, float, float],
    *,
    cfg: Optional[Dict[str, Any]] = None,
    text_spacing_mm: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Find evenly-spaced short vertical LINE entities ("tick trains") in beam bbox.

    beam_bbox: (xmin, ymin, xmax, ymax) in DXF model space.
    """
    cfg = cfg or {}
    min_ticks = int(cfg.get("min_tick_count", 3))
    pitch_min = float(cfg.get("pitch_min_mm", 50))
    pitch_max = float(cfg.get("pitch_max_mm", 400))
    pitch_cv_max = float(cfg.get("pitch_cv_max", 0.35))
    tol = float(cfg.get("text_spacing_tolerance_mm", 15))

    xmin, ymin, xmax, ymax = beam_bbox
    pad_x = max(50.0, (xmax - xmin) * 0.05)
    pad_y = max(50.0, (ymax - ymin) * 0.15)
    xmin -= pad_x
    xmax += pad_x
    ymin -= pad_y
    ymax += pad_y

    candidates: List[Dict[str, Any]] = []
    rejected: List[str] = []

    for e in msp.query("LINE"):
        pts = _line_endpoints(e)
        if not pts:
            continue
        x1, y1, x2, y2 = pts
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        if not (xmin <= mx <= xmax and ymin <= my <= ymax):
            continue
        if not _is_short_vertical(x1, y1, x2, y2):
            continue
        layer = str(e.dxf.layer or "")
        handle = str(getattr(e.dxf, "handle", "") or "")
        candidates.append({
            "x": mx,
            "y": my,
            "length": math.hypot(x2 - x1, y2 - y1),
            "layer": layer,
            "handle": handle,
        })

    if len(candidates) < min_ticks:
        return {
            "detection_method": "vector_elevation_ticks",
            "accepted": False,
            "reject_reason": f"tick_count={len(candidates)} < {min_ticks}",
            "tick_positions_mm": [],
            "measured_pitch_mm": [],
            "zone_count_estimate": 0,
            "text_spacing_agreement": "no_text_to_compare" if text_spacing_mm is None else False,
            "confidence": 0.0,
            "source_entities": [],
            "rejected_notes": rejected + [f"raw_candidates={len(candidates)}"],
        }

    # Cluster by Y band (elevation row), take densest band
    candidates.sort(key=lambda c: c["y"])
    best_band: List[Dict[str, Any]] = []
    y_tol = max(40.0, (ymax - ymin) * 0.08)
    i = 0
    while i < len(candidates):
        band = [candidates[i]]
        j = i + 1
        while j < len(candidates) and abs(candidates[j]["y"] - candidates[i]["y"]) <= y_tol:
            band.append(candidates[j])
            j += 1
        if len(band) > len(best_band):
            best_band = band
        i = j

    best_band = sorted(best_band, key=lambda c: c["x"])
    xs = [c["x"] for c in best_band]
    if len(xs) < min_ticks:
        return {
            "detection_method": "vector_elevation_ticks",
            "accepted": False,
            "reject_reason": f"band_tick_count={len(xs)} < {min_ticks}",
            "tick_positions_mm": [],
            "measured_pitch_mm": [],
            "zone_count_estimate": 0,
            "text_spacing_agreement": "no_text_to_compare" if text_spacing_mm is None else False,
            "confidence": 0.0,
            "source_entities": [],
            "rejected_notes": [f"best_band={len(xs)}"],
        }

    # Origin-relative positions along beam axis (local mm from leftmost tick)
    x0 = xs[0]
    positions = [round(x - x0, 2) for x in xs]
    pitches = [round(positions[i + 1] - positions[i], 2) for i in range(len(positions) - 1)]

    # Filter implausible pitches — keep largest contiguous run in range
    in_range = [pitch_min <= p <= pitch_max for p in pitches]
    if sum(in_range) < min_ticks - 1:
        rejected.append(
            f"pitches_out_of_range count_in={sum(in_range)} pitches={pitches[:12]}"
        )
        return {
            "detection_method": "vector_elevation_ticks",
            "accepted": False,
            "reject_reason": "pitch_range_filter",
            "tick_positions_mm": positions,
            "measured_pitch_mm": pitches,
            "zone_count_estimate": 0,
            "text_spacing_agreement": "no_text_to_compare" if text_spacing_mm is None else False,
            "confidence": 0.0,
            "source_entities": [c["handle"] for c in best_band if c.get("handle")],
            "rejected_notes": rejected,
            "filter_thresholds": {
                "min_tick_count": min_ticks,
                "pitch_min_mm": pitch_min,
                "pitch_max_mm": pitch_max,
                "pitch_cv_max": pitch_cv_max,
            },
        }

    med = statistics.median(pitches) if pitches else None
    if med is None or not (pitch_min <= med <= pitch_max):
        return {
            "detection_method": "vector_elevation_ticks",
            "accepted": False,
            "reject_reason": f"median_pitch_out_of_range:{med}",
            "tick_positions_mm": positions,
            "measured_pitch_mm": pitches,
            "zone_count_estimate": 0,
            "text_spacing_agreement": (
                "no_text_to_compare" if text_spacing_mm is None else False
            ),
            "confidence": 0.0,
            "source_entities": [c["handle"] for c in best_band if c.get("handle")],
            "filter_thresholds": {
                "min_tick_count": min_ticks,
                "pitch_min_mm": pitch_min,
                "pitch_max_mm": pitch_max,
                "pitch_cv_max": pitch_cv_max,
            },
            "rejected_notes": rejected + [f"median_pitch={med}"],
        }

    # Zone estimate from pitch clustering (simple 1D change-points)
    zones = _estimate_zones_from_pitches(pitches)
    cv = _cv(pitches)
    if cv > pitch_cv_max and len(set(round(p / 25.0) * 25.0 for p in pitches)) < 2:
        # Uneven single-pitch train — likely noise, not stirrups
        return {
            "detection_method": "vector_elevation_ticks",
            "accepted": False,
            "reject_reason": f"pitch_cv_too_high:{round(cv, 3)}",
            "tick_positions_mm": positions,
            "measured_pitch_mm": pitches,
            "median_pitch_mm": round(med, 2),
            "zone_count_estimate": 0,
            "text_spacing_agreement": (
                "no_text_to_compare" if text_spacing_mm is None else False
            ),
            "confidence": 0.0,
            "source_entities": [c["handle"] for c in best_band if c.get("handle")],
            "rejected_notes": rejected,
        }

    conf = 0.55
    if cv <= pitch_cv_max:
        conf = 0.75
    if len(positions) >= 8 and cv <= 0.2:
        conf = 0.85

    agreement: Any = "no_text_to_compare"
    if text_spacing_mm is not None:
        agreement = bool(abs(med - text_spacing_mm) <= tol)
        if agreement:
            conf = min(0.95, conf + 0.1)
        else:
            conf = max(0.35, conf - 0.15)

    return {
        "detection_method": "vector_elevation_ticks",
        "accepted": True,
        "tick_positions_mm": positions,
        "measured_pitch_mm": pitches,
        "zone_count_estimate": zones["zone_count"],
        "zone_boundaries_mm": zones["boundaries_mm"],
        "zone_pitches_mm": zones["zone_pitches_mm"],
        "text_spacing_agreement": agreement,
        "text_spacing_mm": text_spacing_mm,
        "median_pitch_mm": round(med, 2),
        "pitch_cv": round(cv, 4),
        "confidence": round(conf, 3),
        "source_entities": [c["handle"] for c in best_band if c.get("handle")],
        "source_layers": sorted({c["layer"] for c in best_band}),
        "filter_thresholds": {
            "min_tick_count": min_ticks,
            "pitch_min_mm": pitch_min,
            "pitch_max_mm": pitch_max,
            "pitch_cv_max": pitch_cv_max,
        },
        "rejected_notes": rejected,
    }


def detect_section_rectangles(
    msp,
    beam_bbox: Tuple[float, float, float, float],
) -> Dict[str, Any]:
    """Closed LWPOLYLINE small rectangles near section cut (secondary vector path)."""
    xmin, ymin, xmax, ymax = beam_bbox
    rects = []
    for e in msp.query("LWPOLYLINE"):
        try:
            if not bool(e.closed):
                continue
            pts = [(float(p[0]), float(p[1])) for p in e.get_points("xy")]
            if len(pts) < 4:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            w = max(xs) - min(xs)
            h = max(ys) - min(ys)
            if w <= 0 or h <= 0:
                continue
            # stirrup section symbols are small relative to beam
            if w > 400 or h > 400 or w < 20 or h < 20:
                continue
            cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
            if not (xmin - 500 <= cx <= xmax + 500 and ymin - 500 <= cy <= ymax + 500):
                continue
            rects.append({
                "cx": cx, "cy": cy, "w": w, "h": h,
                "handle": str(getattr(e.dxf, "handle", "") or ""),
                "layer": str(e.dxf.layer or ""),
            })
        except Exception:
            continue

    if not rects:
        return {
            "detection_method": "vector_section",
            "accepted": False,
            "reject_reason": "no_section_rectangles",
            "tick_positions_mm": [],
            "measured_pitch_mm": [],
            "zone_count_estimate": 0,
            "text_spacing_agreement": "no_text_to_compare",
            "confidence": 0.0,
            "source_entities": [],
        }

    return {
        "detection_method": "vector_section",
        "accepted": True,
        "section_rectangles": rects,
        "tick_positions_mm": [],
        "measured_pitch_mm": [],
        "zone_count_estimate": 1,
        "text_spacing_agreement": "no_text_to_compare",
        "confidence": 0.5,
        "source_entities": [r["handle"] for r in rects if r.get("handle")],
    }


def _estimate_zones_from_pitches(pitches: List[float]) -> Dict[str, Any]:
    if not pitches:
        return {"zone_count": 0, "boundaries_mm": [], "zone_pitches_mm": []}
    # Round pitches to nearest 25mm for clustering
    rounded = [round(p / 25.0) * 25.0 for p in pitches]
    boundaries = [0.0]
    zone_pitches = [rounded[0]]
    cum = 0.0
    for i, p in enumerate(pitches):
        cum += p
        r = rounded[i]
        if abs(r - zone_pitches[-1]) >= 25.0:
            boundaries.append(round(cum - p, 2))
            zone_pitches.append(r)
    # end boundary added by caller via span
    return {
        "zone_count": len(zone_pitches),
        "boundaries_mm": boundaries,
        "zone_pitches_mm": zone_pitches,
    }
