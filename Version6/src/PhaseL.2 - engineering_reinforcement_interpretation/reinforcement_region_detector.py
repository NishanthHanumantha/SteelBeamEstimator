"""Detect reinforcement regions (top zone, bottom zone, side zone, transverse zone)."""

from __future__ import annotations

from typing import Any, Dict, List

from bar_position_analyzer import BarRecord
from beam_reinforcement_model import (
    ZONE_TOP, ZONE_BOTTOM, ZONE_SIDE, ZONE_TRANSVERSE, BeamGeometry,
)


class ReinforcementRegion:
    """A detected zone in the beam containing a group of bars."""

    def __init__(self, zone: str, bars: List[BarRecord]) -> None:
        self.zone = zone
        self.bars = bars
        self.diameter_range = (
            (min(b.diameter_mm for b in bars), max(b.diameter_mm for b in bars))
            if bars else (0.0, 0.0)
        )

    @property
    def bar_count(self) -> int:
        return len(self.bars)

    @property
    def unique_diameters(self) -> List[float]:
        return sorted(set(b.diameter_mm for b in self.bars))


class ReinforcementRegionDetector:
    """Group bars into top/bottom/side/transverse regions."""

    def detect(
        self,
        bars: List[BarRecord],
        geometry: BeamGeometry,
    ) -> Dict[str, ReinforcementRegion]:
        top_bars = [b for b in bars if b.pipeline_role == "TOP_MAIN"]
        bottom_bars = [b for b in bars if b.pipeline_role == "BOTTOM_MAIN"]
        side_bars = [b for b in bars if b.is_side]
        transverse_bars = [b for b in bars if b.is_transverse]

        # If there are bars with larger diameter among "top" bars,
        # they may belong to the bottom zone
        top_reclassified_to_bottom = []
        remaining_top = []
        if top_bars:
            all_dias = sorted(set(b.diameter_mm for b in top_bars), reverse=True)
            if len(all_dias) >= 2:
                max_dia = all_dias[0]
                second_dia = all_dias[1]
                if max_dia - second_dia >= 4.0:
                    # Largest-diameter group → likely bottom
                    top_reclassified_to_bottom = [b for b in top_bars if b.diameter_mm == max_dia]
                    remaining_top = [b for b in top_bars if b.diameter_mm != max_dia]
                else:
                    remaining_top = top_bars
            else:
                remaining_top = top_bars

        bottom_all = bottom_bars + top_reclassified_to_bottom

        return {
            ZONE_TOP: ReinforcementRegion(ZONE_TOP, remaining_top),
            ZONE_BOTTOM: ReinforcementRegion(ZONE_BOTTOM, bottom_all),
            ZONE_SIDE: ReinforcementRegion(ZONE_SIDE, side_bars),
            ZONE_TRANSVERSE: ReinforcementRegion(ZONE_TRANSVERSE, transverse_bars),
        }
