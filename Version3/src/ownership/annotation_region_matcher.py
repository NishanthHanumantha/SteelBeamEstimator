"""Phase D.3.3 — match annotations to detail region envelopes."""

import math
from typing import Any, Dict, List, Tuple

from src.utils.bbox_utils import (
    bbox_centroid,
    distance_point_to_bbox,
    expand_bbox,
    point_in_bbox,
    union_bbox,
)

from src.ownership.ownership_types import REGION_MARGIN_MM


class AnnotationRegionMatcher:
    """Find detail regions that physically contain an annotation."""

    def __init__(self, regions: List[dict[str, Any]]) -> None:
        self._regions = regions
        self._geometry = self._build_geometry(regions)

    def candidates(
        self,
        eval_x: float,
        eval_y: float,
        insert_x: float,
        insert_y: float,
    ) -> List[dict[str, Any]]:
        hits: List[dict[str, Any]] = []
        for geom in self._geometry:
            inside_eval = point_in_bbox(
                eval_x, eval_y, geom["ownership_envelope"], 0.0
            )
            inside_insert = point_in_bbox(
                insert_x, insert_y, geom["ownership_envelope"], 0.0
            )
            dist = distance_point_to_bbox(eval_x, eval_y, geom["sketch_bbox"])
            if inside_eval or inside_insert or dist <= REGION_MARGIN_MM * 2:
                hits.append(
                    {
                        "region_id": geom["region_id"],
                        "region": geom["region"],
                        "sketch_bbox": geom["sketch_bbox"],
                        "ownership_envelope": geom["ownership_envelope"],
                        "inside_eval": inside_eval,
                        "inside_insert": inside_insert,
                        "distance": dist,
                    }
                )
        if not hits:
            nearest = min(
                self._geometry,
                key=lambda g: distance_point_to_bbox(
                    eval_x, eval_y, g["sketch_bbox"]
                ),
            )
            hits.append(
                {
                    "region_id": nearest["region_id"],
                    "region": nearest["region"],
                    "sketch_bbox": nearest["sketch_bbox"],
                    "ownership_envelope": nearest["ownership_envelope"],
                    "inside_eval": False,
                    "inside_insert": False,
                    "distance": distance_point_to_bbox(
                        eval_x, eval_y, nearest["sketch_bbox"]
                    ),
                }
            )
        return hits

    def region_containment_score(
        self,
        candidate: dict[str, Any],
        eval_x: float,
        eval_y: float,
        insert_x: float,
        insert_y: float,
    ) -> float:
        envelope = candidate["ownership_envelope"]
        if point_in_bbox(eval_x, eval_y, envelope, 0.0):
            return 15.0
        if point_in_bbox(insert_x, insert_y, envelope, 0.0):
            return 12.0
        dist = candidate["distance"]
        if dist <= REGION_MARGIN_MM:
            return 10.0
        if dist <= REGION_MARGIN_MM * 2:
            return 6.0
        if dist <= REGION_MARGIN_MM * 4:
            return 3.0
        return 0.0

    def _build_geometry(
        self, regions: List[dict[str, Any]]
    ) -> List[dict[str, Any]]:
        geometry: List[dict[str, Any]] = []
        for region in regions:
            sketches = region.get("member_sketches", [])
            if not sketches:
                continue
            sketch_bbox = union_bbox([s["bbox"] for s in sketches])
            geometry.append(
                {
                    "region_id": region["region_id"],
                    "region": region,
                    "sketch_bbox": sketch_bbox,
                    "ownership_envelope": expand_bbox(
                        sketch_bbox, REGION_MARGIN_MM
                    ),
                }
            )
        return geometry
