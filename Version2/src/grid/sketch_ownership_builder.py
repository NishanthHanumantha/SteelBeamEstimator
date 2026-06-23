"""Phase C.5 — assign sketches to nearest header occurrence per beam mark."""

import math
from typing import Any, Dict, List, Tuple, TypedDict

from loguru import logger

from src.framing.beam_geometry import beam_mark_sort_key
from src.grid.beam_cell_builder import ROW_Y_TOLERANCE_MM
from src.grid.header_occurrence_exporter import HeaderOccurrenceRecord

ROW_CROSSING_Y_TOLERANCE_MM = ROW_Y_TOLERANCE_MM


class SketchOwnershipRecord(TypedDict):
    beam_mark: str
    occurrence_id: int
    owned_sketches: List[str]


class SketchAssignment(TypedDict):
    sketch_id: str
    beam_mark: str
    occurrence_id: int


class SketchOwnershipBuilder:
    """Map each sketch to the nearest header occurrence of the same beam mark."""

    def assign(
        self,
        occurrences: List[HeaderOccurrenceRecord],
        sketches: List[dict[str, Any]],
    ) -> Tuple[List[SketchOwnershipRecord], List[SketchAssignment]]:
        occurrence_index = self._index_occurrences(occurrences)
        row_by_occurrence = self._assign_occurrence_rows(occurrences)

        assignments: List[SketchAssignment] = []
        sketch_owners: Dict[str, Tuple[str, int]] = {}

        for sketch in sketches:
            sketch_id = str(sketch["sketch_id"])
            mark = str(sketch["beam_mark"]).upper()
            centroid = self._sketch_centroid(sketch)

            mark_occurrences = occurrence_index.get(mark, [])
            if not mark_occurrences:
                logger.warning(
                    "No header occurrences for beam mark {} — sketch {} orphan",
                    mark,
                    sketch_id,
                )
                continue

            nearest = min(
                mark_occurrences,
                key=lambda occ: self._distance(centroid, (occ["x"], occ["y"])),
            )

            if sketch_id in sketch_owners:
                logger.warning("Sketch {} already assigned — skipping duplicate", sketch_id)
                continue

            sketch_owners[sketch_id] = (mark, nearest["occurrence_id"])
            assignments.append(
                SketchAssignment(
                    sketch_id=sketch_id,
                    beam_mark=mark,
                    occurrence_id=nearest["occurrence_id"],
                )
            )

        ownership = self._build_ownership_records(occurrences, assignments)
        logger.info(
            "Assigned {} sketch(s) to {} header occurrence(s)",
            len(assignments),
            sum(1 for record in ownership if record["owned_sketches"]),
        )
        return ownership, assignments

    def _build_ownership_records(
        self,
        occurrences: List[HeaderOccurrenceRecord],
        assignments: List[SketchAssignment],
    ) -> List[SketchOwnershipRecord]:
        owned: Dict[Tuple[str, int], List[str]] = {
            (occ["beam_mark"], occ["occurrence_id"]): []
            for occ in occurrences
        }

        for assignment in assignments:
            key = (assignment["beam_mark"], assignment["occurrence_id"])
            owned.setdefault(key, []).append(assignment["sketch_id"])

        records: List[SketchOwnershipRecord] = []
        for occurrence in occurrences:
            key = (occurrence["beam_mark"], occurrence["occurrence_id"])
            sketches = sorted(
                owned.get(key, []),
                key=lambda sketch_id: self._sketch_sort_key(sketch_id),
            )
            records.append(
                SketchOwnershipRecord(
                    beam_mark=occurrence["beam_mark"],
                    occurrence_id=occurrence["occurrence_id"],
                    owned_sketches=sketches,
                )
            )

        records.sort(
            key=lambda record: (
                beam_mark_sort_key(record["beam_mark"]),
                record["occurrence_id"],
            )
        )
        return records

    def _index_occurrences(
        self, occurrences: List[HeaderOccurrenceRecord]
    ) -> Dict[str, List[HeaderOccurrenceRecord]]:
        index: Dict[str, List[HeaderOccurrenceRecord]] = {}
        for occurrence in occurrences:
            index.setdefault(occurrence["beam_mark"], []).append(occurrence)
        return index

    def _assign_occurrence_rows(
        self, occurrences: List[HeaderOccurrenceRecord]
    ) -> Dict[Tuple[str, int], int]:
        """Cluster header occurrences into rows by Y; return (mark, id) -> row_id."""
        sorted_occurrences = sorted(
            occurrences,
            key=lambda occ: (-occ["y"], occ["x"], beam_mark_sort_key(occ["beam_mark"])),
        )

        rows: List[List[HeaderOccurrenceRecord]] = []
        for occurrence in sorted_occurrences:
            placed = False
            for row in rows:
                row_y = sum(item["y"] for item in row) / len(row)
                if abs(occurrence["y"] - row_y) <= ROW_Y_TOLERANCE_MM:
                    row.append(occurrence)
                    placed = True
                    break
            if not placed:
                rows.append([occurrence])

        rows.sort(
            key=lambda row: sum(item["y"] for item in row) / len(row),
            reverse=True,
        )

        row_map: Dict[Tuple[str, int], int] = {}
        for row_id, row in enumerate(rows, start=1):
            for occurrence in row:
                row_map[(occurrence["beam_mark"], occurrence["occurrence_id"])] = row_id
        return row_map

    def find_row_crossings(
        self,
        occurrences: List[HeaderOccurrenceRecord],
        sketches: List[dict[str, Any]],
        assignments: List[SketchAssignment],
    ) -> List[str]:
        """Flag sketches assigned across distant rows when the mark has a nearer-row header."""
        row_by_occurrence = self._assign_occurrence_rows(occurrences)
        sketch_rows = self._sketch_row_map(occurrences, sketches)
        sketch_by_id = {str(sketch["sketch_id"]): sketch for sketch in sketches}

        crossings: List[str] = []
        for assignment in assignments:
            sketch_id = assignment["sketch_id"]
            owner_key = (assignment["beam_mark"], assignment["occurrence_id"])
            owner_row = row_by_occurrence.get(owner_key)
            sketch_row = sketch_rows.get(sketch_id)
            sketch = sketch_by_id.get(sketch_id)

            if owner_row is None or sketch_row is None or sketch is None:
                continue
            if abs(owner_row - sketch_row) < 2:
                continue

            mark = assignment["beam_mark"]
            same_mark_in_sketch_row = [
                occ
                for occ in occurrences
                if occ["beam_mark"] == mark
                and row_by_occurrence.get((occ["beam_mark"], occ["occurrence_id"]))
                == sketch_row
            ]
            if not same_mark_in_sketch_row:
                continue

            centroid = self._sketch_centroid(sketch)
            nearest_in_sketch_row = min(
                same_mark_in_sketch_row,
                key=lambda occ: self._distance(centroid, (occ["x"], occ["y"])),
            )
            if nearest_in_sketch_row["occurrence_id"] != assignment["occurrence_id"]:
                crossings.append(sketch_id)

        return sorted(crossings, key=self._sketch_sort_key)

    def _sketch_row_map(
        self,
        occurrences: List[HeaderOccurrenceRecord],
        sketches: List[dict[str, Any]],
    ) -> Dict[str, int]:
        row_centers = self._row_center_ys(occurrences)
        sketch_rows: Dict[str, int] = {}
        for sketch in sketches:
            sketch_id = str(sketch["sketch_id"])
            _, cy = self._sketch_centroid(sketch)
            if not row_centers:
                continue
            nearest_row = min(
                range(len(row_centers)),
                key=lambda index: abs(cy - row_centers[index]),
            )
            sketch_rows[sketch_id] = nearest_row + 1
        return sketch_rows

    def _row_center_ys(
        self, occurrences: List[HeaderOccurrenceRecord]
    ) -> List[float]:
        row_by_occurrence = self._assign_occurrence_rows(occurrences)
        rows: Dict[int, List[float]] = {}
        for occurrence in occurrences:
            key = (occurrence["beam_mark"], occurrence["occurrence_id"])
            row_id = row_by_occurrence[key]
            rows.setdefault(row_id, []).append(occurrence["y"])
        return [
            sum(rows[row_id]) / len(rows[row_id])
            for row_id in sorted(rows)
        ]

    @staticmethod
    def _sketch_centroid(sketch: dict[str, Any]) -> Tuple[float, float]:
        bbox = sketch["bbox"]
        cx = (float(bbox["xmin"]) + float(bbox["xmax"])) / 2.0
        cy = (float(bbox["ymin"]) + float(bbox["ymax"])) / 2.0
        return cx, cy

    @staticmethod
    def _distance(
        point: Tuple[float, float], other: Tuple[float, float]
    ) -> float:
        return math.hypot(point[0] - other[0], point[1] - other[1])

    @staticmethod
    def _sketch_sort_key(sketch_id: str) -> Tuple[str, int]:
        if "_S" in sketch_id:
            mark, suffix = sketch_id.rsplit("_S", maxsplit=1)
            try:
                return (mark, int(suffix))
            except ValueError:
                pass
        return (sketch_id, 0)
