"""Validation for Phase C beam cell segmentation."""

from typing import List, TypedDict

from src.framing.beam_geometry import beam_mark_sort_key
from src.grid.beam_cell_builder import BeamCell
from src.reinforcement.header_extractor import ReinforcementHeader


class BeamCellValidation(TypedDict):
    row_count: int
    beams_per_row: dict[str, int]
    overlapping_cells: List[str]
    orphan_headers: List[str]


class BeamCellValidator:
    """Build beam_cells_validation.json payload."""

    def validate(
        self,
        cells: List[BeamCell],
        source_headers: List[ReinforcementHeader],
    ) -> BeamCellValidation:
        beams_per_row: dict[str, int] = {}
        for cell in cells:
            key = str(cell["row_id"])
            beams_per_row[key] = beams_per_row.get(key, 0) + 1

        overlapping_cells = self._find_overlaps(cells)
        cell_marks = {cell["beam_mark"] for cell in cells}
        orphan_headers = sorted(
            [
                header["beam_mark"]
                for header in source_headers
                if header["beam_mark"] not in cell_marks
            ],
            key=beam_mark_sort_key,
        )

        return BeamCellValidation(
            row_count=len(beams_per_row),
            beams_per_row=beams_per_row,
            overlapping_cells=overlapping_cells,
            orphan_headers=orphan_headers,
        )

    def _find_overlaps(self, cells: List[BeamCell]) -> List[str]:
        overlaps: List[str] = []
        by_row: dict[int, List[BeamCell]] = {}
        for cell in cells:
            by_row.setdefault(cell["row_id"], []).append(cell)

        for row_cells in by_row.values():
            row_cells.sort(key=lambda cell: cell["xmin"])
            for left, right in zip(row_cells, row_cells[1:]):
                if right["xmin"] < left["xmax"]:
                    pair = f"{left['beam_mark']}/{right['beam_mark']}"
                    if pair not in overlaps:
                        overlaps.append(pair)

        return overlaps
