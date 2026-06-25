"""Phase D.3 — rule-based beam group detection from cells and sketch geometry."""

from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.framing.beam_geometry import beam_mark_sort_key
from src.grouping.beam_group_types import BeamGroup, BeamGroupMember
from src.utils.bbox_utils import (
    bbox_centroid,
    bbox_height,
    detail_band_for_beam,
    horizontal_overlap_ratio,
    sketches_for_beam,
    union_bbox,
    vertical_band_overlap_ratio,
)

CELL_ADJACENCY_TOLERANCE_MM = 5.0
DETAIL_Y_ALIGN_TOLERANCE_MM = 800.0
DETAIL_BAND_MIN_OVERLAP_RATIO = 0.45
DETAIL_HEIGHT_TOLERANCE_RATIO = 0.30
SKETCH_LINK_GAP_TOLERANCE_MM = 2000.0
SKETCH_LINK_MIN_VERTICAL_OVERLAP = 0.30


class BeamGroupBuilder:
    """Detect beam groups that share reinforcement detail layout."""

    def build(
        self,
        beam_cells: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
        header_occurrences: List[dict[str, Any]],
    ) -> List[BeamGroup]:
        cells_by_mark = {str(c["beam_mark"]).upper(): c for c in beam_cells}
        occurrence_index = self._index_occurrences(header_occurrences)
        rows = self._group_cells_by_row(beam_cells)

        provisional_groups: List[List[str]] = []
        for row_id in sorted(rows.keys()):
            row_cells = sorted(rows[row_id], key=lambda c: float(c["xmin"]))
            chains = self._adjacent_chains(row_cells)
            for chain in chains:
                provisional_groups.extend(self._split_chain_by_detail_band(chain, sketches))

        all_marks = sorted(cells_by_mark.keys(), key=beam_mark_sort_key)
        assigned: set[str] = set()
        for group_marks in provisional_groups:
            assigned.update(group_marks)

        for mark in all_marks:
            if mark not in assigned:
                provisional_groups.append([mark])

        sorted_groups = sorted(
            provisional_groups,
            key=lambda marks: beam_mark_sort_key(marks[0]),
        )

        beam_groups: List[BeamGroup] = []
        for index, member_marks in enumerate(sorted_groups, start=1):
            sorted_members = sorted(member_marks, key=beam_mark_sort_key)
            member_details = [
                self._member_detail(mark, cells_by_mark, sketches, occurrence_index)
                for mark in sorted_members
            ]
            cell_bboxes = [m["cell_bbox"] for m in member_details]
            detail_bands = [m["detail_band"] for m in member_details]
            group_bbox = union_bbox(cell_bboxes)
            group_detail = union_bbox(detail_bands)
            cx, cy = bbox_centroid(group_bbox)

            beam_groups.append(
                BeamGroup(
                    beam_group_id=f"GROUP_{index:03d}",
                    members=sorted_members,
                    member_details=member_details,
                    centroid={"x": round(cx, 2), "y": round(cy, 2)},
                    bounding_box=group_bbox,
                    detail_band=group_detail,
                    row_id=int(member_details[0]["row_id"]),
                    is_multi_beam=len(sorted_members) > 1,
                )
            )

        logger.info(
            "Built {} beam group(s) — {} multi-beam",
            len(beam_groups),
            sum(1 for g in beam_groups if g["is_multi_beam"]),
        )
        return beam_groups

    def _index_occurrences(
        self, occurrences: List[dict[str, Any]]
    ) -> Dict[str, List[int]]:
        index: Dict[str, List[int]] = {}
        for occ in occurrences:
            mark = str(occ["beam_mark"]).upper()
            occ_id = int(occ["occurrence_id"])
            index.setdefault(mark, []).append(occ_id)
        for mark in index:
            index[mark] = sorted(set(index[mark]))
        return index

    def _group_cells_by_row(
        self, beam_cells: List[dict[str, Any]]
    ) -> Dict[int, List[dict[str, Any]]]:
        rows: Dict[int, List[dict[str, Any]]] = {}
        for cell in beam_cells:
            row_id = int(cell["row_id"])
            rows.setdefault(row_id, []).append(cell)
        return rows

    def _adjacent_chains(self, row_cells: List[dict[str, Any]]) -> List[List[str]]:
        if not row_cells:
            return []
        chains: List[List[str]] = []
        current = [str(row_cells[0]["beam_mark"]).upper()]
        for idx in range(1, len(row_cells)):
            cell = row_cells[idx]
            mark = str(cell["beam_mark"]).upper()
            prev = row_cells[idx - 1]
            gap = float(cell["xmin"]) - float(prev["xmax"])
            if gap <= CELL_ADJACENCY_TOLERANCE_MM:
                current.append(mark)
            else:
                chains.append(current)
                current = [mark]
        chains.append(current)
        return chains

    def _split_chain_by_detail_band(
        self,
        chain: List[str],
        sketches: List[dict[str, Any]],
    ) -> List[List[str]]:
        if len(chain) <= 1:
            return [chain]

        groups: List[List[str]] = []
        current_group = [chain[0]]
        current_band = detail_band_for_beam(chain[0], sketches)

        for mark in chain[1:]:
            beam_band = detail_band_for_beam(mark, sketches)
            if current_band is None or beam_band is None:
                if len(current_group) > 1:
                    groups.append(current_group)
                else:
                    groups.append([current_group[0]])
                current_group = [mark]
                current_band = beam_band
                continue

            if self._detail_bands_compatible(current_band, beam_band) and self._sketches_link_beams(
                current_group[-1], mark, sketches
            ):
                current_group.append(mark)
                current_band = union_bbox([current_band, beam_band])
            else:
                groups.append(current_group)
                current_group = [mark]
                current_band = beam_band

        groups.append(current_group)
        return groups

    def _detail_bands_compatible(self, band_a: Dict[str, float], band_b: Dict[str, float]) -> bool:
        ymin_delta = abs(band_a["ymin"] - band_b["ymin"])
        ymax_delta = abs(band_a["ymax"] - band_b["ymax"])
        if ymin_delta <= DETAIL_Y_ALIGN_TOLERANCE_MM and ymax_delta <= DETAIL_Y_ALIGN_TOLERANCE_MM:
            return True

        overlap_ratio = vertical_band_overlap_ratio(band_a, band_b)
        if overlap_ratio >= DETAIL_BAND_MIN_OVERLAP_RATIO:
            height_a = bbox_height(band_a)
            height_b = bbox_height(band_b)
            max_height = max(height_a, height_b)
            if max_height > 0.0:
                height_delta = abs(height_a - height_b) / max_height
                if height_delta <= DETAIL_HEIGHT_TOLERANCE_RATIO:
                    return True
        return False

    def _sketches_link_beams(
        self,
        beam_a: str,
        beam_b: str,
        sketches: List[dict[str, Any]],
    ) -> bool:
        sketches_a = sketches_for_beam(beam_a, sketches)
        sketches_b = sketches_for_beam(beam_b, sketches)
        if not sketches_a or not sketches_b:
            return False

        for sketch_a in sketches_a:
            bbox_a = sketch_a["bbox"]
            for sketch_b in sketches_b:
                bbox_b = sketch_b["bbox"]
                if horizontal_overlap_ratio(bbox_a, bbox_b) > 0.01:
                    return True
                vertical_overlap = vertical_band_overlap_ratio(bbox_a, bbox_b)
                if vertical_overlap < SKETCH_LINK_MIN_VERTICAL_OVERLAP:
                    continue
                gap_ab = bbox_b["xmin"] - bbox_a["xmax"]
                gap_ba = bbox_a["xmin"] - bbox_b["xmax"]
                if -50.0 <= gap_ab <= SKETCH_LINK_GAP_TOLERANCE_MM:
                    return True
                if -50.0 <= gap_ba <= SKETCH_LINK_GAP_TOLERANCE_MM:
                    return True
        return False

    def _member_detail(
        self,
        beam_mark: str,
        cells_by_mark: Dict[str, dict[str, Any]],
        sketches: List[dict[str, Any]],
        occurrence_index: Dict[str, List[int]],
    ) -> BeamGroupMember:
        cell = cells_by_mark[beam_mark]
        beam_sketches = sketches_for_beam(beam_mark, sketches)
        detail = detail_band_for_beam(beam_mark, sketches) or {
            "xmin": float(cell["xmin"]),
            "ymin": float(cell["ymin"]),
            "xmax": float(cell["xmax"]),
            "ymax": float(cell["ymax"]),
        }
        return BeamGroupMember(
            beam_mark=beam_mark,
            row_id=int(cell["row_id"]),
            cell_bbox={
                "xmin": float(cell["xmin"]),
                "ymin": float(cell["ymin"]),
                "xmax": float(cell["xmax"]),
                "ymax": float(cell["ymax"]),
            },
            detail_band=detail,
            sketch_ids=[str(s["sketch_id"]) for s in beam_sketches],
            occurrence_ids=occurrence_index.get(beam_mark, []),
        )
