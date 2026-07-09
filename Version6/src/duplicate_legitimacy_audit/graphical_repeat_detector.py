"""Detect purely graphical repeated annotations."""

from __future__ import annotations

from typing import Any, Dict, List

from src.duplicate_legitimacy_audit.annotation_context import AnnotationContextBuilder
from src.duplicate_legitimacy_audit.duplicate_group_loader import COORDINATE_TOLERANCE


class GraphicalRepeatDetector:
    """Determine whether duplicate members are graphical repeats."""

    def analyze(self, group: dict[str, Any], contexts: List[dict[str, Any]]) -> dict[str, Any]:
        members = group.get("members") or []
        pairs = 0
        equal_pairs = 0
        for index, left in enumerate(members):
            for right in members[index + 1 :]:
                pairs += 1
                if AnnotationContextBuilder.coordinates_equal(
                    left.get("coordinates") or {},
                    right.get("coordinates") or {},
                    COORDINATE_TOLERANCE,
                ):
                    equal_pairs += 1
        all_equal = pairs > 0 and equal_pairs == pairs
        any_equal = equal_pairs > 0
        return {
            "pair_count": pairs,
            "equal_coordinate_pairs": equal_pairs,
            "all_coordinates_equal": all_equal,
            "any_coordinates_equal": any_equal,
            "graphical_repeat_likely": all_equal or (any_equal and len(members) <= 3),
        }
