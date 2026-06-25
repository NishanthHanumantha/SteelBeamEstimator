"""Phase D.3.2 — detail region detection from sketch geometry."""

from typing import Any, Dict, List, Set

from loguru import logger

from src.framing.beam_geometry import beam_mark_sort_key
from src.grouping.beam_group_builder import BeamGroupBuilder
from src.utils.bbox_utils import sketches_for_beam, union_bbox
from src.utils.sketch_linking import build_cell_adjacency, sketch_clusters

SKETCH_CELL_MARGIN_MM = 800.0


class DetailRegionDetector:
    """Detect reinforcement detail regions from sketch linkage (primary object)."""

    def detect(
        self,
        sketches: List[dict[str, Any]],
        beam_cells: List[dict[str, Any]],
        header_occurrences: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        cell_adjacency = build_cell_adjacency(beam_cells)
        filtered_sketches = self._filter_sketches_to_cells(sketches, beam_cells)
        beam_groups = BeamGroupBuilder().build(
            beam_cells, filtered_sketches, header_occurrences
        )

        candidates: List[dict[str, Any]] = []
        beams_in_multi: Set[str] = set()

        for group in beam_groups:
            marks = list(group["members"])
            group_sketches = [
                s
                for s in filtered_sketches
                if str(s["beam_mark"]).upper() in marks
            ]
            clusters = sketch_clusters(group_sketches, cell_adjacency)

            if group["is_multi_beam"] and len(clusters) > 1:
                for mark in marks:
                    beam_sketches = sketches_for_beam(mark, filtered_sketches)
                    if not beam_sketches:
                        continue
                    candidates.append(
                        self._region_candidate(
                            beam_sketches,
                            [mark],
                            is_multi_beam=False,
                            cell_adjacency=cell_adjacency,
                        )
                    )
                beams_in_multi.update(marks)
                continue

            candidates.append(
                self._region_candidate(
                    group_sketches,
                    marks,
                    is_multi_beam=group["is_multi_beam"],
                    cell_adjacency=cell_adjacency,
                )
            )
            if group["is_multi_beam"]:
                beams_in_multi.update(marks)

        all_marks = sorted(
            {str(c["beam_mark"]).upper() for c in beam_cells},
            key=beam_mark_sort_key,
        )
        assigned = {m for c in candidates for m in c["beam_titles"]}
        for mark in all_marks:
            if mark in assigned:
                continue
            beam_sketches = sketches_for_beam(mark, filtered_sketches)
            if not beam_sketches:
                continue
            candidates.append(
                self._region_candidate(
                    beam_sketches,
                    [mark],
                    is_multi_beam=False,
                    cell_adjacency=cell_adjacency,
                )
            )

        candidates.sort(key=lambda r: beam_mark_sort_key(r["beam_titles"][0]))
        for index, region in enumerate(candidates, start=1):
            region["region_id"] = f"DETAIL_REGION_{index:03d}"

        logger.info(
            "Detected {} detail region candidate(s) — {} multi-beam",
            len(candidates),
            sum(1 for c in candidates if c["is_multi_beam"]),
        )
        return candidates

    def _filter_sketches_to_cells(
        self,
        sketches: List[dict[str, Any]],
        beam_cells: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        """Drop sketches whose horizontal center lies outside the owning beam cell."""
        cell_by_mark = {str(c["beam_mark"]).upper(): c for c in beam_cells}
        kept: List[dict[str, Any]] = []
        dropped = 0
        for sketch in sketches:
            mark = str(sketch["beam_mark"]).upper()
            cell = cell_by_mark.get(mark)
            if cell is None:
                kept.append(sketch)
                continue
            bbox = sketch["bbox"]
            cx = (float(bbox["xmin"]) + float(bbox["xmax"])) / 2.0
            xmin = float(cell["xmin"]) - SKETCH_CELL_MARGIN_MM
            xmax = float(cell["xmax"]) + SKETCH_CELL_MARGIN_MM
            if xmin <= cx <= xmax:
                kept.append(sketch)
            else:
                dropped += 1
        if dropped:
            logger.info(
                "Filtered {} sketch(es) outside owning beam cell envelope",
                dropped,
            )
        return kept

    def _region_candidate(
        self,
        sketches: List[dict[str, Any]],
        beam_titles: List[str],
        is_multi_beam: bool,
        cell_adjacency: Set[frozenset[str]],
    ) -> dict[str, Any]:
        sketch_bbox = union_bbox([s["bbox"] for s in sketches])
        clusters = sketch_clusters(sketches, cell_adjacency)
        sorted_titles = sorted(beam_titles, key=beam_mark_sort_key)
        return {
            "bbox": sketch_bbox,
            "sketch_bbox": sketch_bbox,
            "beam_titles": sorted_titles,
            "member_sketches": [
                {
                    "sketch_id": str(s["sketch_id"]),
                    "beam_mark": str(s["beam_mark"]).upper(),
                    "bbox": s["bbox"],
                }
                for s in sketches
            ],
            "is_multi_beam": is_multi_beam,
            "sketch_cluster_count": len(clusters),
            "continuous_sketch_linkage": len(clusters) == 1,
        }
