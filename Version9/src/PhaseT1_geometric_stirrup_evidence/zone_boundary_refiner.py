"""
T1.4 — Type3 zone boundary refinement from pitch changes / SupportLocations.
MODEL_VERSION: 9.3.0
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

MODEL_VERSION = "9.3.0"

_TYPE3_RE = re.compile(
    r"@\s*(\d+(?:\s*/\s*\d+)+)",
    re.I,
)


def parse_type3_spacings(label: str) -> List[int]:
    """Parse 100/200/100 from a stirrup callout label."""
    if not label:
        return []
    m = _TYPE3_RE.search(label.replace("\\P", "").replace(" ", ""))
    if not m:
        return []
    parts = [int(x) for x in re.findall(r"\d+", m.group(1))]
    return parts if len(parts) >= 2 else []


def refine_zone_boundaries(
    span_mm: float,
    spacings_mm: Sequence[int],
    *,
    geometry_evidence: Optional[Dict[str, Any]] = None,
    supports: Optional[List[Dict[str, Any]]] = None,
    prefer_pitch_change: bool = True,
    prefer_support_locations: bool = True,
) -> Dict[str, Any]:
    """
    Return zone segments with start/end/spacing.

    Priority:
      1) Measured pitch-change boundaries from T1.2 (if confident)
      2) SupportLocations-anchored zones
      3) Legacy equal-N fallback (caller may also use 0.25L)
    """
    n = len(spacings_mm)
    if span_mm <= 0 or n <= 0:
        return {
            "method": "none",
            "segments": [],
            "fallback_used": True,
        }

    if n == 1:
        return {
            "method": "uniform",
            "segments": [{
                "zone_name": "Zone_A",
                "start_mm": 0.0,
                "end_mm": span_mm,
                "spacing_mm": int(spacings_mm[0]),
            }],
            "fallback_used": False,
        }

    # 1) Pitch-change boundaries
    if prefer_pitch_change and geometry_evidence and geometry_evidence.get("accepted"):
        bounds = list(geometry_evidence.get("zone_boundaries_mm") or [])
        zone_pitches = list(geometry_evidence.get("zone_pitches_mm") or [])
        conf = float(geometry_evidence.get("confidence") or 0)
        if conf >= 0.55 and len(bounds) >= 1 and len(zone_pitches) == n:
            ends = bounds[1:] + [span_mm]
            starts = [float(b) for b in bounds]
            # rescale if last measured extent differs from span
            measured_end = ends[-1] if ends else span_mm
            if measured_end > 1 and abs(measured_end - span_mm) / span_mm > 0.15:
                scale = span_mm / measured_end
                starts = [s * scale for s in starts]
                ends = [e * scale for e in ends]
            else:
                ends[-1] = span_mm
            segs = []
            for i, sp in enumerate(spacings_mm):
                start = starts[i] if i < len(starts) else i * span_mm / n
                end = ends[i] if i < len(ends) else (i + 1) * span_mm / n
                segs.append({
                    "zone_name": f"Zone_{chr(ord('A') + i)}",
                    "start_mm": round(start, 1),
                    "end_mm": round(end, 1),
                    "spacing_mm": int(sp),
                })
            return {
                "method": "pitch_change",
                "segments": segs,
                "fallback_used": False,
                "evidence": ["t1_pitch_change_boundaries"],
            }

    # 2) SupportLocations — left/right support faces + mid remainder
    if prefer_support_locations and supports:
        left = next((s for s in supports if s.get("support_type") == "LEFT_SUPPORT"), None)
        right = next((s for s in supports if s.get("support_type") == "RIGHT_SUPPORT"), None)
        if left and right and n >= 3:
            # use zone_end of left support / zone_start of right if present
            left_end = float(
                left.get("zone_end_fraction") or left.get("position_fraction") or 0.25
            ) * span_mm
            right_start = float(
                right.get("zone_start_fraction") or right.get("position_fraction") or 0.75
            ) * span_mm
            if 0 < left_end < right_start < span_mm:
                mid_sp = int(spacings_mm[1]) if n >= 3 else int(spacings_mm[-1])
                support_sp = int(spacings_mm[0])
                segs = [
                    {"zone_name": "Zone_A", "start_mm": 0.0, "end_mm": round(left_end, 1),
                     "spacing_mm": support_sp},
                    {"zone_name": "Zone_B", "start_mm": round(left_end, 1),
                     "end_mm": round(right_start, 1), "spacing_mm": mid_sp},
                    {"zone_name": "Zone_C", "start_mm": round(right_start, 1),
                     "end_mm": round(span_mm, 1), "spacing_mm": int(spacings_mm[-1])},
                ]
                return {
                    "method": "support_locations",
                    "segments": segs,
                    "fallback_used": False,
                    "evidence": ["support_locations_json"],
                }

    # 3) Equal-N fallback
    zone_len = span_mm / float(n)
    segs = []
    for i, sp in enumerate(spacings_mm):
        segs.append({
            "zone_name": f"Zone_{chr(ord('A') + i)}",
            "start_mm": round(i * zone_len, 1),
            "end_mm": round((i + 1) * zone_len, 1),
            "spacing_mm": int(sp),
        })
    return {
        "method": "equal_n_fallback",
        "segments": segs,
        "fallback_used": True,
        "evidence": ["equal_n_legacy"],
    }
