"""Phase D.3.2 — assign beam titles and refine region membership."""

from typing import Any, Dict, List, Set, Tuple

from loguru import logger

from src.framing.beam_geometry import beam_mark_sort_key
from src.utils.bbox_utils import (
    distance_point_to_bbox,
    expand_bbox,
    point_in_bbox,
    sketches_for_beam,
    union_bbox,
)
from src.utils.sketch_linking import build_cell_adjacency, sketch_clusters

TITLE_ASSIGN_MARGIN_MM = 800.0


class DetailRegionRefiner:
    """Ensure each beam title belongs to exactly one detail region."""

    def refine(
        self,
        regions: List[dict[str, Any]],
        header_occurrences: List[dict[str, Any]],
        beam_cells: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        cell_adjacency = build_cell_adjacency(beam_cells)
        cell_by_mark = {str(c["beam_mark"]).upper(): c for c in beam_cells}

        regions = self._split_non_continuous_multi_beam(
            regions, sketches, cell_adjacency
        )
        regions = self._assign_titles(regions, header_occurrences, cell_by_mark, sketches)
        regions = self.split_disconnected(regions, beam_cells)
        return regions

    def _split_non_continuous_multi_beam(
        self,
        regions: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
        cell_adjacency: Set[frozenset[str]],
    ) -> List[dict[str, Any]]:
        """Split multi-beam regions that lack one continuous sketch cluster."""
        result: List[dict[str, Any]] = []
        split_count = 0

        for region in regions:
            if not region.get("is_multi_beam"):
                result.append(region)
                continue
            if region.get("sketch_cluster_count", 1) <= 1:
                result.append(region)
                continue

            split_count += 1
            for mark in region["beam_titles"]:
                beam_sketches = sketches_for_beam(mark, sketches)
                if not beam_sketches:
                    continue
                clusters = sketch_clusters(beam_sketches, cell_adjacency)
                result.append(
                    {
                        "bbox": union_bbox([s["bbox"] for s in beam_sketches]),
                        "sketch_bbox": union_bbox([s["bbox"] for s in beam_sketches]),
                        "beam_titles": [mark],
                        "member_sketches": [
                            {
                                "sketch_id": str(s["sketch_id"]),
                                "beam_mark": mark,
                                "bbox": s["bbox"],
                            }
                            for s in beam_sketches
                        ],
                        "is_multi_beam": False,
                        "sketch_cluster_count": len(clusters),
                        "continuous_sketch_linkage": len(clusters) == 1,
                    }
                )

        if split_count:
            logger.info(
                "Split {} non-continuous multi-beam region(s) into single-beam regions",
                split_count,
            )
        return result

    def _assign_titles(
        self,
        regions: List[dict[str, Any]],
        header_occurrences: List[dict[str, Any]],
        cell_by_mark: Dict[str, dict[str, Any]],
        sketches: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        """Assign titles from sketch ownership; nearest region for beams without sketches."""
        for region in regions:
            sketch_marks = {
                str(s["beam_mark"]).upper() for s in region.get("member_sketches", [])
            }
            region["beam_titles"] = sorted(sketch_marks, key=beam_mark_sort_key)
            region["is_multi_beam"] = len(region["beam_titles"]) > 1

        mark_to_region: Dict[str, str] = {}
        for region in regions:
            for mark in region["beam_titles"]:
                mark_to_region[mark] = region["region_id"]

        all_headers = self._all_headers(header_occurrences)
        for mark, hx, hy in all_headers:
            if mark in mark_to_region:
                continue
            if sketches_for_beam(mark, sketches):
                owning = self._region_for_sketch_owner(mark, regions)
                if owning is not None:
                    owning["beam_titles"] = sorted(
                        set(owning["beam_titles"]) | {mark},
                        key=beam_mark_sort_key,
                    )
                    mark_to_region[mark] = owning["region_id"]
                    continue

            nearest = self._nearest_region_for_header(
                mark, hx, hy, regions, cell_by_mark
            )
            if nearest is None:
                continue
            nearest["beam_titles"] = sorted(
                set(nearest["beam_titles"]) | {mark},
                key=beam_mark_sort_key,
            )
            mark_to_region[mark] = nearest["region_id"]

        for region in regions:
            region["assigned_titles"] = region["beam_titles"]
            region["is_multi_beam"] = len(region["beam_titles"]) > 1

        logger.info(
            "Assigned {} beam title(s) across {} region(s)",
            len(mark_to_region),
            len(regions),
        )
        return regions

    def _region_for_sketch_owner(
        self, mark: str, regions: List[dict[str, Any]]
    ) -> dict[str, Any] | None:
        for region in regions:
            for sketch in region.get("member_sketches", []):
                if str(sketch["beam_mark"]).upper() == mark:
                    return region
        return None

    def _nearest_region_for_header(
        self,
        mark: str,
        hx: float,
        hy: float,
        regions: List[dict[str, Any]],
        cell_by_mark: Dict[str, dict[str, Any]],
    ) -> dict[str, Any] | None:
        cell = cell_by_mark.get(mark)
        candidates = regions
        if cell is not None:
            cx = (float(cell["xmin"]) + float(cell["xmax"])) / 2.0
            in_column = [
                r
                for r in regions
                if r["sketch_bbox"]["xmin"] <= cx <= r["sketch_bbox"]["xmax"]
            ]
            if in_column:
                candidates = in_column

        return min(
            candidates,
            key=lambda r: distance_point_to_bbox(hx, hy, r["sketch_bbox"]),
        )

    def _all_headers(
        self, occurrences: List[dict[str, Any]]
    ) -> List[Tuple[str, float, float]]:
        seen: Set[str] = set()
        headers: List[Tuple[str, float, float]] = []
        for occ in occurrences:
            mark = str(occ["beam_mark"]).upper()
            if mark in seen:
                continue
            seen.add(mark)
            headers.append((mark, float(occ["x"]), float(occ["y"])))
        return sorted(headers, key=lambda h: beam_mark_sort_key(h[0]))

    def split_disconnected(
        self,
        regions: List[dict[str, Any]],
        beam_cells: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        """Split multi-beam regions when sketch continuity breaks between beams."""
        cell_adjacency = build_cell_adjacency(beam_cells)
        result: List[dict[str, Any]] = []
        split_count = 0

        for region in regions:
            if not region.get("is_multi_beam"):
                result.append(region)
                continue

            sketch_payload = [
                {
                    "sketch_id": s["sketch_id"],
                    "beam_mark": s["beam_mark"],
                    "bbox": s["bbox"],
                }
                for s in region.get("member_sketches", [])
            ]
            clusters = sketch_clusters(sketch_payload, cell_adjacency)
            if len(clusters) <= 1:
                result.append(region)
                continue

            split_count += 1
            for cluster in clusters:
                marks = sorted(
                    {str(s["beam_mark"]).upper() for s in cluster},
                    key=beam_mark_sort_key,
                )
                sub = dict(region)
                sub["member_sketches"] = [
                    {
                        "sketch_id": str(s["sketch_id"]),
                        "beam_mark": str(s["beam_mark"]).upper(),
                        "bbox": s["bbox"],
                    }
                    for s in cluster
                ]
                sub["beam_titles"] = marks
                sub["assigned_titles"] = marks
                sub["is_multi_beam"] = len(marks) >= 2
                sub["sketch_cluster_count"] = 1
                sub["continuous_sketch_linkage"] = True
                sub["sketch_bbox"] = union_bbox([s["bbox"] for s in cluster])
                sub["bbox"] = sub["sketch_bbox"]
                sub.pop("member_annotations", None)
                result.append(sub)

        if split_count:
            logger.info("Split {} disconnected multi-beam region(s)", split_count)
        return result
