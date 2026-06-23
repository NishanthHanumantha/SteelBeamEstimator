"""Validation for Phase B reinforcement header extraction."""

import re
from typing import List, TypedDict

from src.framing.beam_geometry import beam_mark_sort_key
from src.reinforcement.header_extractor import ReinforcementHeader

_BEAM_MARK_NUMBER = re.compile(r"^B(\d+)$", re.IGNORECASE)


class ReinforcementHeaderValidation(TypedDict):
    total_headers: int
    duplicate_headers: List[str]
    missing_headers: List[str]
    sorted_beam_list: List[str]


class ReinforcementHeaderValidator:
    """Build reinforcement_header_validation.json payload."""

    def validate(
        self,
        all_occurrences: List[ReinforcementHeader],
        output_headers: List[ReinforcementHeader],
    ) -> ReinforcementHeaderValidation:
        occurrence_counts: dict[str, int] = {}
        for header in all_occurrences:
            mark = header["beam_mark"]
            occurrence_counts[mark] = occurrence_counts.get(mark, 0) + 1

        duplicate_headers = sorted(
            [mark for mark, count in occurrence_counts.items() if count > 1],
            key=beam_mark_sort_key,
        )

        sorted_beam_list = sorted(
            {header["beam_mark"] for header in output_headers},
            key=beam_mark_sort_key,
        )
        missing_headers = self._find_sequence_gaps(sorted_beam_list)

        return ReinforcementHeaderValidation(
            total_headers=len(all_occurrences),
            duplicate_headers=duplicate_headers,
            missing_headers=missing_headers,
            sorted_beam_list=sorted_beam_list,
        )

    def _find_sequence_gaps(self, marks: List[str]) -> List[str]:
        numbers: List[int] = []
        for mark in marks:
            match = _BEAM_MARK_NUMBER.match(mark)
            if match:
                numbers.append(int(match.group(1)))

        if not numbers:
            return []

        numbers.sort()
        missing: List[str] = []
        for value in range(numbers[0], numbers[-1] + 1):
            if value not in numbers:
                missing.append(f"B{value}")
        return missing
