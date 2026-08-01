"""
OpenCV raster fallback for exploded / unavailable vector geometry.
MODEL_VERSION: 9.3.0
"""
from __future__ import annotations

import math
import statistics
from pathlib import Path
from typing import Any, Dict, Optional

MODEL_VERSION = "9.3.0"


def detect_ticks_opencv(
    png_path: Path,
    *,
    cfg: Optional[Dict[str, Any]] = None,
    text_spacing_mm: Optional[float] = None,
    mm_per_px: Optional[float] = None,
    fallback_reason: str = "vector_geometry_unavailable",
) -> Dict[str, Any]:
    """Hough-line clustering on geometry-only render (text OFF)."""
    cfg = cfg or {}
    min_ticks = int(cfg.get("min_tick_count", 3))
    pitch_min = float(cfg.get("pitch_min_mm", 50))
    pitch_max = float(cfg.get("pitch_max_mm", 400))
    tol = float(cfg.get("text_spacing_tolerance_mm", 15))

    base = {
        "detection_method": "opencv_fallback",
        "fallback_reason": fallback_reason,
        "tick_positions_mm": [],
        "measured_pitch_mm": [],
        "zone_count_estimate": 0,
        "text_spacing_agreement": (
            "no_text_to_compare" if text_spacing_mm is None else False
        ),
        "confidence": 0.0,
        "source_entities": [],
        "accepted": False,
    }

    try:
        import cv2
    except ImportError:
        base["reject_reason"] = "opencv_not_installed"
        return base

    if not png_path.exists():
        base["reject_reason"] = "png_missing"
        return base

    img = cv2.imread(str(png_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        base["reject_reason"] = "png_unreadable"
        return base

    edges = cv2.Canny(img, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges, 1, math.pi / 180.0, threshold=40,
        minLineLength=8, maxLineGap=3,
    )
    if lines is None:
        base["reject_reason"] = "no_hough_lines"
        return base

    scale = float(mm_per_px or 1.0)
    xs = []
    for line in lines[:, 0]:
        x1, y1, x2, y2 = map(float, line)
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        if dy < 5 or (dx / max(dy, 1e-6)) > 0.4:
            continue
        xs.append((x1 + x2) / 2.0)

    if len(xs) < min_ticks:
        base["reject_reason"] = f"tick_count={len(xs)} < {min_ticks}"
        return base

    xs = sorted(xs)
    dedup = [xs[0]]
    for x in xs[1:]:
        if abs(x - dedup[-1]) * scale >= pitch_min * 0.4:
            dedup.append(x)
    positions = [round((x - dedup[0]) * scale, 2) for x in dedup]
    pitches = [round(positions[i + 1] - positions[i], 2) for i in range(len(positions) - 1)]
    pitches_ok = [p for p in pitches if pitch_min <= p <= pitch_max]
    if len(pitches_ok) < min_ticks - 1:
        base["reject_reason"] = "pitch_range_filter"
        base["tick_positions_mm"] = positions
        base["measured_pitch_mm"] = pitches
        return base

    med = statistics.median(pitches_ok) if pitches_ok else None
    agreement: Any = "no_text_to_compare"
    if text_spacing_mm is not None and med is not None:
        agreement = abs(med - text_spacing_mm) <= tol

    return {
        "detection_method": "opencv_fallback",
        "accepted": True,
        "fallback_reason": fallback_reason,
        "tick_positions_mm": positions,
        "measured_pitch_mm": pitches,
        "median_pitch_mm": round(med, 2) if med is not None else None,
        "zone_count_estimate": 1,
        "text_spacing_agreement": agreement,
        "confidence": 0.45,
        "source_entities": [],
    }
