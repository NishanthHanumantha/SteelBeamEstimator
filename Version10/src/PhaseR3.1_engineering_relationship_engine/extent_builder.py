"""
extent_builder.py — Build extent evidence for all detected physical bars.
MODEL_VERSION: 8.1.0

Delegates to BarGeometryBuilder per bar.
Provides a convenient batch interface for the orchestrator.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .bar_geometry_builder import BarGeometryBuilder
from .relationship_models import PhysicalBar


class ExtentBuilder:
    """Batch-build extent evidence for all detected bars."""

    def __init__(self):
        self._geo = BarGeometryBuilder()

    def build_all(
        self,
        bars:          List[PhysicalBar],
        supports_by_beam: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Tuple]:
        """
        Returns: {bar_id: (extent_label, confidence, reason, left_crossed, right_crossed)}
        """
        result: Dict[str, Tuple] = {}

        for bar in bars:
            support_data = supports_by_beam.get(bar.beam_id, [])
            ext = self._geo.compute_extent(bar, support_data)
            result[bar.bar_id] = ext

        return result
