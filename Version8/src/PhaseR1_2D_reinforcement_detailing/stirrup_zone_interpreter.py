"""
Stirrup zone interpreter — multi-spacing segmentation.
MODEL_VERSION: 8.4.0
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "8.4.0"

_SPACING_RE = re.compile(r"@\s*(\d+)", re.I)
_LEGS_RE = re.compile(r"(\d+)\s*L", re.I)
_DENSITY = 7850.0


def parse_spacing(label: str, spacing_field: Optional[float] = None) -> Optional[float]:
    if spacing_field is not None:
        return float(spacing_field)
    if not label:
        return None
    m = _SPACING_RE.search(label)
    return float(m.group(1)) if m else None


def parse_legs(label: str) -> int:
    if not label:
        return 2
    m = _LEGS_RE.search(label.replace(" ", ""))
    return int(m.group(1)) if m else 2


class StirrupZoneInterpreter:
    """
    Interpret stirrup spacing into Zone A/B/C segments.

    When a beam has multiple distinct spacings (e.g. @100 and @150),
    assign tighter spacing to support zones and looser to mid-span
    (engineering convention 100-150-100 / 150-200-150 etc.).
    Single spacing → one mid/full segment with explicit evidence (not silent full-span).
    """

    def interpret_beam(
        self,
        beam_id: str,
        stirrup_intents: List[Any],
        span_mm: float,
        depth_mm: float = 450.0,
        width_mm: float = 230.0,
    ) -> Dict[str, Any]:
        """
        Returns {
          intent_id: {segments, spacing_pattern, zone_count, evidence, confidence},
          ...
          "_beam_pattern": ...
        }
        """
        if not stirrup_intents:
            return {}

        # Collect unique spacings with representative intents
        by_spacing: Dict[float, List[Any]] = {}
        for it in stirrup_intents:
            sp = parse_spacing(str(getattr(it, "bar_label", "") or ""), getattr(it, "spacing_mm", None))
            if sp is None:
                continue
            by_spacing.setdefault(sp, []).append(it)

        spacings = sorted(by_spacing.keys())
        span = max(float(span_mm or 0), 0.0)
        result: Dict[str, Any] = {}

        if not spacings:
            for it in stirrup_intents:
                result[it.intent_id] = {
                    "segments": [],
                    "spacing_pattern": "",
                    "zone_count": 0,
                    "spacing_mm": None,
                    "confidence": 0.3,
                    "evidence": ["stirrup_spacing_unparsed"],
                }
            return result

        if len(spacings) == 1:
            sp = spacings[0]
            pattern = f"{int(sp)}"
            segs = self._single_zone(span, sp, depth_mm, width_mm)
            for it in by_spacing[sp]:
                result[it.intent_id] = {
                    "segments": segs,
                    "spacing_pattern": pattern,
                    "zone_count": 1,
                    "spacing_mm": sp,
                    "confidence": 0.85,
                    "evidence": [
                        f"single_spacing={sp}",
                        "not_assumed_multi_zone",
                        f"span_mm={span}",
                    ],
                }
            result["_beam_pattern"] = pattern
            return result

        # Multi-spacing: tighter at supports, looser at mid
        tight = min(spacings)
        loose = max(spacings)
        # Optional middle spacing
        mid_sp = None
        if len(spacings) == 3:
            mid_sp = spacings[1]
        elif len(spacings) > 3:
            mid_sp = spacings[len(spacings) // 2]

        if mid_sp is not None:
            pattern = f"{int(tight)}-{int(mid_sp)}-{int(tight)}"
            segs = self._three_zone(span, tight, mid_sp, depth_mm, width_mm)
        else:
            pattern = f"{int(tight)}-{int(loose)}-{int(tight)}"
            segs = self._three_zone(span, tight, loose, depth_mm, width_mm)

        # Map each intent to the segment matching its spacing
        for sp, intents in by_spacing.items():
            matching = [s for s in segs if abs(s["spacing_mm"] - sp) < 0.5]
            if not matching:
                matching = [s for s in segs if s["spacing_mm"] == sp] or segs[:1]
            for it in intents:
                result[it.intent_id] = {
                    "segments": matching if matching else segs,
                    "all_beam_segments": segs,
                    "spacing_pattern": pattern,
                    "zone_count": len(segs),
                    "spacing_mm": sp,
                    "confidence": 0.88,
                    "evidence": [
                        f"multi_spacing_beam={spacings}",
                        f"pattern={pattern}",
                        f"assigned_spacing={sp}",
                        "tighter_at_supports_convention",
                    ],
                }
        result["_beam_pattern"] = pattern
        result["_beam_segments"] = segs
        return result

    def _single_zone(
        self, span: float, spacing: float, depth: float, width: float
    ) -> List[Dict[str, Any]]:
        if span <= 0 or spacing <= 0:
            return [{
                "zone_name": "Zone_A",
                "start_mm": 0.0,
                "end_mm": max(span, 0.0),
                "spacing_mm": spacing or 0.0,
                "quantity": 0,
                "length_mm": 0.0,
                "weight_kg": None,
                "confidence": 0.4,
                "evidence": ["span_or_spacing_missing"],
            }]
        qty = max(1, int(math.floor(span / spacing)) + 1)
        cut = self._stirrup_cut(depth, width, 8.0)
        return [{
            "zone_name": "Zone_A",
            "start_mm": 0.0,
            "end_mm": span,
            "spacing_mm": spacing,
            "quantity": qty,
            "length_mm": cut * qty,
            "weight_kg": round(self._weight(8.0, cut, qty), 4),
            "confidence": 0.85,
            "evidence": ["single_zone_along_available_span"],
        }]

    def _three_zone(
        self,
        span: float,
        support_sp: float,
        mid_sp: float,
        depth: float,
        width: float,
    ) -> List[Dict[str, Any]]:
        if span <= 0:
            return []
        # Support zones ~0.25L each side, mid remainder (generalized)
        left_end = span * 0.25
        right_start = span * 0.75
        cut = self._stirrup_cut(depth, width, 8.0)

        def seg(name, start, end, sp):
            length = max(0.0, end - start)
            qty = max(1, int(math.floor(length / sp)) + 1) if sp > 0 and length > 0 else 0
            return {
                "zone_name": name,
                "start_mm": round(start, 1),
                "end_mm": round(end, 1),
                "spacing_mm": sp,
                "quantity": qty,
                "length_mm": round(cut * qty, 1),
                "weight_kg": round(self._weight(8.0, cut, qty), 4),
                "confidence": 0.88,
                "evidence": [f"zone={name}", f"spacing={sp}", "0.25L_support_split"],
            }

        return [
            seg("Zone_A", 0.0, left_end, support_sp),
            seg("Zone_B", left_end, right_start, mid_sp),
            seg("Zone_C", right_start, span, support_sp),
        ]

    @staticmethod
    def _stirrup_cut(depth: float, width: float, dia: float) -> float:
        # Approximate closed stirrup perimeter + hooks
        return 2.0 * (depth + width) + 20.0 * dia

    @staticmethod
    def _weight(dia: float, cut_mm: float, qty: int) -> float:
        area = math.pi * dia * dia / 4.0
        return area * cut_mm * qty * _DENSITY / 1e9
