"""Analyze bar position within beam section using available geometry evidence."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from beam_reinforcement_model import (
    ZONE_TOP, ZONE_BOTTOM, ZONE_SIDE, ZONE_TRANSVERSE, ZONE_UNKNOWN,
    EXTENT_FULL, EXTENT_PARTIAL, EXTENT_SUPPORT_LEFT, EXTENT_SUPPORT_RIGHT,
    EXTENT_SUPPORT_BOTH, EXTENT_UNKNOWN,
)

# Transverse bar roles from pipeline
TRANSVERSE_PIPELINE_ROLES = {"STIRRUP", "LINK_BAR", "TRANSVERSE"}
# Side bar roles from pipeline
SIDE_PIPELINE_ROLES = {"SIDE_BAR", "EDGE_BAR", "SIDE_FACE"}


class BarRecord:
    """Lightweight bar record used during interpretation."""

    def __init__(
        self,
        bar_id: str,
        beam_id: str,
        pipeline_role: str,
        diameter_mm: float,
        quantity: int,
        steel_grade: str = "Y",
        spacing_mm: Optional[float] = None,
        support_hint: Optional[str] = None,
        source_bar_id: Optional[str] = None,
    ) -> None:
        self.bar_id = bar_id
        self.beam_id = beam_id
        self.pipeline_role = pipeline_role
        self.diameter_mm = diameter_mm
        self.quantity = quantity
        self.steel_grade = steel_grade
        self.spacing_mm = spacing_mm
        self.support_hint = support_hint  # "LEFT_SUPPORT" / "RIGHT_SUPPORT" / None
        self.source_bar_id = source_bar_id

    @property
    def bar_label(self) -> str:
        if self.spacing_mm:
            return f"{self.quantity}L-{self.steel_grade}{int(self.diameter_mm)}@{int(self.spacing_mm)}"
        return f"{self.quantity}{self.steel_grade}{int(self.diameter_mm)}"

    @property
    def is_transverse(self) -> bool:
        return self.pipeline_role.upper() in TRANSVERSE_PIPELINE_ROLES

    @property
    def is_side(self) -> bool:
        return self.pipeline_role.upper() in SIDE_PIPELINE_ROLES


class BarPositionAnalyzer:
    """Determine position zone and extent for each bar based on pipeline evidence."""

    def analyze(
        self,
        bar: BarRecord,
        beam_bars: List[BarRecord],
        geometry: Optional[Any],
    ) -> Tuple[str, str, Optional[float]]:
        """
        Returns (position_zone, extent, coverage_ratio).
        Uses pipeline role + diameter analysis + support hints.
        """
        if bar.is_transverse:
            return ZONE_TRANSVERSE, EXTENT_FULL, 1.0

        if bar.is_side:
            return ZONE_SIDE, EXTENT_FULL, 1.0

        # Determine TOP vs BOTTOM zone from available evidence
        zone = self._determine_zone(bar, beam_bars)
        extent, ratio = self._determine_extent(bar, beam_bars, geometry)
        return zone, extent, ratio

    def _determine_zone(self, bar: BarRecord, beam_bars: List[BarRecord]) -> str:
        """
        Determine TOP or BOTTOM zone for longitudinal bars.
        Uses diameter analysis: in simply-supported beams, larger-diameter bars
        tend to be the primary tension (bottom) reinforcement.
        """
        if bar.pipeline_role.upper() == "TOP_MAIN":
            # Check if this is likely misclassified as top
            # Collect all unique diameters in the beam (longitudinal only)
            long_bars = [b for b in beam_bars if not b.is_transverse and not b.is_side]
            all_dias = sorted(set(b.diameter_mm for b in long_bars), reverse=True)

            # If there are multiple diameter groups, the largest-diameter bars
            # at a unique diameter level could be bottom main
            # (Only apply if we have clear size differentiation)
            if len(all_dias) >= 2 and bar.diameter_mm == max(all_dias):
                max_dia = max(all_dias)
                second_dia = all_dias[1] if len(all_dias) > 1 else 0
                # Clear size jump (>= 4mm) suggests bottom bars are misclassified
                if max_dia - second_dia >= 4.0:
                    return ZONE_BOTTOM
            return ZONE_TOP

        if bar.pipeline_role.upper() == "BOTTOM_MAIN":
            return ZONE_BOTTOM
        if bar.pipeline_role.upper() == "SIDE_BAR":
            return ZONE_SIDE

        return ZONE_UNKNOWN

    def _determine_extent(
        self,
        bar: BarRecord,
        beam_bars: List[BarRecord],
        geometry: Optional[Any],
    ) -> Tuple[str, Optional[float]]:
        """Determine FULL_SPAN vs PARTIAL_SPAN extent."""
        # Support hint from recovery data
        if bar.support_hint:
            if "LEFT" in bar.support_hint.upper():
                return EXTENT_SUPPORT_LEFT, 0.2
            if "RIGHT" in bar.support_hint.upper():
                return EXTENT_SUPPORT_RIGHT, 0.2

        # Multiplicity check: if same (dia, qty) spec appears multiple times in beam
        # and there's also a "full span" version, the repeats are support bars
        same_spec = [
            b for b in beam_bars
            if b.diameter_mm == bar.diameter_mm
            and b.quantity == bar.quantity
            and b.pipeline_role == bar.pipeline_role
            and not b.is_transverse and not b.is_side
        ]

        if len(same_spec) >= 2:
            # Multiple groups of same spec → one is full span, others are support extras
            # The first occurrence is treated as full span (continuous), rest are support extras
            if same_spec[0].bar_id == bar.bar_id:
                return EXTENT_FULL, 1.0
            else:
                return EXTENT_SUPPORT_BOTH, 0.35

        return EXTENT_FULL, 1.0
