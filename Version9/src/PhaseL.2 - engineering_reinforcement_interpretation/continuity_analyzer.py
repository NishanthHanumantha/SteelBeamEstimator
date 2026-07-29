"""Detect continuity type for reinforcement bars."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from bar_position_analyzer import BarRecord
from beam_reinforcement_model import (
    ContinuityRegion,
    CONTINUITY_SINGLE, CONTINUITY_MULTI, CONTINUITY_SHARED, CONTINUITY_UNKNOWN,
    EXTENT_FULL, EXTENT_PARTIAL,
)

# Multi-span continuous groups (bars run through multiple beams)
CONTINUOUS_GROUPS: Dict[str, List[str]] = {
    "B8": ["B8", "B9", "B10"],
    "B9": ["B8", "B9", "B10"],
    "B10": ["B8", "B9", "B10"],
}


class ContinuityAnalyzer:
    """Determine whether bars are single-beam, continuous-multi-beam, or shared."""

    def analyze(
        self,
        beam_id: str,
        bars: List[BarRecord],
        extent_map: Dict[str, str],
    ) -> str:
        """Return continuity type for this beam."""
        if beam_id in CONTINUOUS_GROUPS:
            return CONTINUITY_MULTI
        return CONTINUITY_SINGLE

    def build_continuity_regions(
        self,
        beam_bars_map: Dict[str, List[BarRecord]],
    ) -> List[ContinuityRegion]:
        regions: List[ContinuityRegion] = []
        processed: set = set()
        counter = [0]

        def _id() -> str:
            counter[0] += 1
            return f"CONT::L2::{counter[0]:04d}"

        # Build continuous regions for multi-span groups
        for group in [["B8", "B9", "B10"]]:
            group_key = ",".join(group)
            if group_key in processed:
                continue
            processed.add(group_key)
            bar_ids: List[str] = []
            for bm in group:
                for b in (beam_bars_map.get(bm) or []):
                    bar_ids.append(b.bar_id)
            if bar_ids:
                regions.append(ContinuityRegion(
                    region_id=_id(),
                    beam_ids=group,
                    bar_ids=bar_ids,
                    continuity_type=CONTINUITY_MULTI,
                ))

        # Single-beam continuity regions for all other beams
        for beam_id, bars in beam_bars_map.items():
            if beam_id in CONTINUOUS_GROUPS:
                continue
            if bars:
                regions.append(ContinuityRegion(
                    region_id=_id(),
                    beam_ids=[beam_id],
                    bar_ids=[b.bar_id for b in bars],
                    continuity_type=CONTINUITY_SINGLE,
                ))
        return regions
