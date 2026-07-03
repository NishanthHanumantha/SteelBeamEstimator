"""Validation for Phase A framing beam extraction."""

from typing import Any, List, TypedDict

from src.framing.beam_geometry import beam_mark_sort_key
from src.framing.framing_beam_extractor import FramingBeam


class FramingValidation(TypedDict):
    total_beams_detected: int
    duplicate_beams: List[str]
    missing_dimensions: List[str]
    beam_marks: List[str]


class FramingValidator:
    """Build framing_validation.json payload."""

    def validate(self, beams: List[FramingBeam]) -> FramingValidation:
        mark_counts: dict[str, int] = {}
        missing_dimensions: List[str] = []

        for beam in beams:
            mark = beam["beam_mark"]
            mark_counts[mark] = mark_counts.get(mark, 0) + 1
            if (
                beam["width_mm"] <= 0
                or beam["depth_mm"] <= 0
                or beam["length_mm"] <= 0
            ):
                missing_dimensions.append(mark)

        duplicate_beams = sorted(
            [mark for mark, count in mark_counts.items() if count > 1],
            key=beam_mark_sort_key,
        )
        beam_marks = sorted(mark_counts.keys(), key=beam_mark_sort_key)

        return FramingValidation(
            total_beams_detected=len(beams),
            duplicate_beams=duplicate_beams,
            missing_dimensions=sorted(set(missing_dimensions), key=beam_mark_sort_key),
            beam_marks=beam_marks,
        )
