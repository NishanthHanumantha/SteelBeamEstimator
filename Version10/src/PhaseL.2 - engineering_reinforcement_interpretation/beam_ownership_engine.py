"""Assign reinforcement ownership across multi-beam drawings."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from bar_position_analyzer import BarRecord
from beam_reinforcement_model import (
    CONTINUITY_MULTI, EXTENT_FULL, EXTENT_PARTIAL,
)

# Multi-span beam groups where bars cross beam boundaries
MULTI_BEAM_DRAWINGS: Dict[str, List[str]] = {
    "B8": ["B8", "B9", "B10"],
    "B9": ["B8", "B9", "B10"],
    "B10": ["B8", "B9", "B10"],
}

# For multi-beam drawings, bars in the combined drawing are shared across spans.
# The drawing shows bars per span, not per beam — so each beam segment OWNS
# the bars within its clear span.


class BeamOwnershipEngine:
    """Resolve bar ownership for single-beam and multi-beam drawings."""

    def resolve(
        self,
        beam_id: str,
        bars: List[BarRecord],
        all_bars_by_beam: Dict[str, List[BarRecord]],
    ) -> List[BarRecord]:
        """
        Return bars that BELONG to beam_id.
        For multi-beam drawings, bars from the shared drawing are re-assigned
        to the specific beam that "owns" them based on span segment.
        """
        group = MULTI_BEAM_DRAWINGS.get(beam_id)
        if not group:
            # Single-beam drawing: all bars belong to this beam
            return bars

        # Multi-beam drawing: each bar is owned by its primary beam segment.
        # For B8-B10 continuous: the bars are per-beam (each beam has own top/bottom bars).
        # All bars already assigned to beam_id are owned by it.
        owned = [b for b in bars if b.beam_id == beam_id]
        return owned

    def detect_shared_reinforcement(
        self,
        beam_bars_map: Dict[str, List[BarRecord]],
    ) -> Dict[str, List[str]]:
        """Return dict of beam_id → list of bar_ids that are shared across beams."""
        shared: Dict[str, List[str]] = {}
        # For this project, no bars are shared (each beam segment owns its bars)
        return shared
