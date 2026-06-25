"""Phase D.3.3 — resolve competing region ownership candidates."""

from typing import Any, Dict, List, Tuple

from src.ownership.annotation_region_matcher import AnnotationRegionMatcher
from src.ownership.annotation_sketch_matcher import AnnotationSketchMatcher
from src.ownership.annotation_confidence import AnnotationConfidence
from src.ownership.ownership_types import (
    AMBIGUITY_MARGIN,
    MIN_OWNERSHIP_SCORE,
    WEIGHT_DISTANCE,
    WEIGHT_GEOMETRY,
    WEIGHT_LEADER,
    WEIGHT_ORIENTATION,
    WEIGHT_REGION,
    WEIGHT_SKETCH,
)


class AnnotationConflictResolver:
    """Pick winning detail region and sketch using weighted geometry scores."""

    def __init__(
        self,
        region_matcher: AnnotationRegionMatcher,
        sketch_matcher: AnnotationSketchMatcher,
    ) -> None:
        self._region_matcher = region_matcher
        self._sketch_matcher = sketch_matcher
        self._confidence = AnnotationConfidence()

    def resolve(
        self,
        insert_x: float,
        insert_y: float,
        eval_x: float,
        eval_y: float,
        has_leader: bool,
        cell_mark: str | None = None,
    ) -> Tuple[dict[str, Any], List[dict[str, Any]]]:
        candidates = self._region_matcher.candidates(
            eval_x, eval_y, insert_x, insert_y
        )
        scored: List[dict[str, Any]] = []

        for candidate in candidates:
            region = candidate["region"]
            sketch, sketch_score, geom_score = self._sketch_matcher.best_sketch(
                region, eval_x, eval_y, insert_x, insert_y, has_leader
            )
            if sketch is None:
                continue

            region_score = self._region_matcher.region_containment_score(
                candidate, eval_x, eval_y, insert_x, insert_y
            )
            distance_score = self._sketch_matcher.distance_score(
                sketch, eval_x, eval_y
            )
            orientation_score = self._sketch_matcher.orientation_score(
                sketch, insert_x, insert_y, eval_x, eval_y
            )
            eval_in_sketch = sketch_score >= 18.0
            leader_score = self._confidence.leader_component(
                has_leader, eval_in_sketch
            )

            total = (
                leader_score
                + min(sketch_score, WEIGHT_SKETCH)
                + min(region_score, WEIGHT_REGION)
                + min(geom_score, WEIGHT_GEOMETRY)
                + min(distance_score, WEIGHT_DISTANCE)
                + min(orientation_score, WEIGHT_ORIENTATION)
            )
            if cell_mark and cell_mark in {
                str(t).upper() for t in region.get("beam_titles", [])
            }:
                total += 20.0

            scored.append(
                {
                    "region_id": candidate["region_id"],
                    "region": region,
                    "sketch": sketch,
                    "total_score": total,
                    "leader_score": leader_score,
                    "sketch_score": sketch_score,
                    "region_score": region_score,
                    "geometry_score": geom_score,
                    "distance_score": distance_score,
                    "orientation_score": orientation_score,
                }
            )

        if not scored:
            return self._empty_result(insert_x, insert_y, eval_x, eval_y, has_leader), []

        scored.sort(key=lambda s: s["total_score"], reverse=True)
        best = scored[0]
        is_ambiguous = False
        if len(scored) > 1:
            margin = scored[0]["total_score"] - scored[1]["total_score"]
            is_ambiguous = margin < AMBIGUITY_MARGIN

        conf = self._confidence.score(
            best["total_score"],
            has_leader,
            best["leader_score"],
            best["sketch_score"],
            best["region_score"],
            best["geometry_score"],
            best["distance_score"],
            best["orientation_score"],
            is_ambiguous,
        )

        status = "OWNED"
        if best["total_score"] < MIN_OWNERSHIP_SCORE:
            status = "UNASSIGNED"
        elif is_ambiguous:
            status = "AMBIGUOUS"

        sketch = best["sketch"]
        result = {
            "ownership_status": status,
            "detail_region_id": best["region_id"],
            "resolved_beam_mark": str(sketch["beam_mark"]).upper(),
            "resolved_sketch_id": str(sketch["sketch_id"]),
            "eval_x": eval_x,
            "eval_y": eval_y,
            "insert_x": insert_x,
            "insert_y": insert_y,
            "has_leader": has_leader,
            "is_ambiguous": is_ambiguous,
            **conf,
        }
        return result, scored

    def _empty_result(
        self,
        insert_x: float,
        insert_y: float,
        eval_x: float,
        eval_y: float,
        has_leader: bool,
    ) -> dict[str, Any]:
        return {
            "ownership_status": "UNASSIGNED",
            "detail_region_id": None,
            "resolved_beam_mark": None,
            "resolved_sketch_id": None,
            "eval_x": eval_x,
            "eval_y": eval_y,
            "insert_x": insert_x,
            "insert_y": insert_y,
            "has_leader": has_leader,
            "is_ambiguous": False,
            "confidence_score": 0,
            "confidence_label": "LOW",
            "component_scores": {
                "leader": 0.0,
                "sketch_overlap": 0.0,
                "region_containment": 0.0,
                "reinforcement_geometry": 0.0,
                "distance": 0.0,
                "orientation": 0.0,
            },
        }
