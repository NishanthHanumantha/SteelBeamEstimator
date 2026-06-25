"""Phase D.3.3 — ownership confidence scoring."""

from typing import Any, Dict

from src.ownership.ownership_types import confidence_label


class AnnotationConfidence:
    """Compute 0-100 ownership confidence from component scores."""

    def score(
        self,
        total_weighted: float,
        has_leader: bool,
        leader_score: float,
        sketch_score: float,
        region_score: float,
        geometry_score: float,
        distance_score: float,
        orientation_score: float,
        is_ambiguous: bool,
    ) -> dict[str, Any]:
        raw = min(100.0, max(0.0, total_weighted))
        if is_ambiguous:
            raw = min(raw, 75.0)
        if not has_leader and raw > 80.0:
            raw = min(raw, 80.0)

        label = confidence_label(raw)
        return {
            "confidence_score": int(round(raw)),
            "confidence_label": label,
            "component_scores": {
                "leader": leader_score,
                "sketch_overlap": sketch_score,
                "region_containment": region_score,
                "reinforcement_geometry": geometry_score,
                "distance": distance_score,
                "orientation": orientation_score,
            },
        }

    def leader_component(self, has_leader: bool, eval_in_sketch: bool) -> float:
        if not has_leader:
            return 0.0
        if eval_in_sketch:
            return 40.0
        return 28.0
