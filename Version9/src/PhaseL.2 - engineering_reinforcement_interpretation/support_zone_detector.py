"""Detect support zones for each beam."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from beam_reinforcement_model import (
    SupportZone, SUPPORT_LEFT, SUPPORT_RIGHT, SUPPORT_INTERMEDIATE,
)

# Multi-span continuous beams from drawing (B8, B9, B10 share a continuous drawing)
CONTINUOUS_BEAM_GROUPS: List[List[str]] = [
    ["B8", "B9", "B10"],
]

# Support width from general notes / framing plan (columns/walls)
DEFAULT_SUPPORT_WIDTH_MM = 200.0


class SupportZoneDetector:
    """Identify left/right/intermediate supports for all beams."""

    def detect(self, beam_ids: List[str], snapshot: Dict[str, Any]) -> Dict[str, List[SupportZone]]:
        # Map beams to their continuous group (if any)
        continuous_map: Dict[str, List[str]] = {}
        for group in CONTINUOUS_BEAM_GROUPS:
            for b in group:
                continuous_map[b] = group

        counter = [0]

        def _id() -> str:
            counter[0] += 1
            return f"SUP::L2::{counter[0]:04d}"

        result: Dict[str, List[SupportZone]] = {}
        for beam_id in beam_ids:
            group = continuous_map.get(beam_id)
            if group:
                idx = group.index(beam_id)
                # Left support
                left_adj = group[idx - 1] if idx > 0 else None
                left_type = SUPPORT_INTERMEDIATE if idx > 0 else SUPPORT_LEFT
                # Right support
                right_adj = group[idx + 1] if idx < len(group) - 1 else None
                right_type = SUPPORT_INTERMEDIATE if idx < len(group) - 1 else SUPPORT_RIGHT
            else:
                left_adj = None
                right_adj = None
                left_type = SUPPORT_LEFT
                right_type = SUPPORT_RIGHT

            result[beam_id] = [
                SupportZone(
                    support_id=_id(),
                    support_type=left_type,
                    beam_id=beam_id,
                    adjacent_beam_id=left_adj,
                    position_fraction=0.0,
                    support_width_mm=DEFAULT_SUPPORT_WIDTH_MM,
                ),
                SupportZone(
                    support_id=_id(),
                    support_type=right_type,
                    beam_id=beam_id,
                    adjacent_beam_id=right_adj,
                    position_fraction=1.0,
                    support_width_mm=DEFAULT_SUPPORT_WIDTH_MM,
                ),
            ]
        return result
