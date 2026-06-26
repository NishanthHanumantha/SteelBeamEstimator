"""Phase D.4.1 — geometry-based position and continuity for longitudinal bars."""

from typing import Any, Dict, Literal, Optional, Tuple

Position = Literal["TOP", "BOTTOM", "UNKNOWN"]
Continuity = Literal["CONTINUOUS", "PARTIAL", "UNKNOWN"]

_POSITION_BAND_RATIO = 0.12
_CONTINUITY_END_RATIO = 0.18


class ReinforcementGeometryClassifier:
    """Infer TOP/BOTTOM and CONTINUOUS/PARTIAL from sketch geometry."""

    def classify_longitudinal(
        self, obj: dict[str, Any]
    ) -> Tuple[Position, Continuity, Dict[str, float]]:
        resolved_position = obj.get("resolved_position")
        resolved_continuity = obj.get("resolved_continuity")
        if resolved_position and resolved_continuity:
            geo = obj.get("geometry_resolution") or {}
            confidence = float(geo.get("confidence", 85))
            return (
                resolved_position,
                resolved_continuity,
                {"geometry_confidence": confidence, "source": "D4.2"},
            )

        bbox = obj.get("sketch_bbox")
        coords = obj.get("coordinates", {})
        leader = obj.get("leader_endpoint")

        if not bbox:
            return "UNKNOWN", "UNKNOWN", {"geometry_confidence": 0.0}

        eval_x = float(coords.get("eval_x", coords.get("x", 0)))
        eval_y = float(coords.get("eval_y", coords.get("y", 0)))
        insert_x = float(coords.get("x", eval_x))
        insert_y = float(coords.get("y", eval_y))

        ref_x, ref_y = eval_x, eval_y
        if leader:
            ref_x = float(leader["x"])
            ref_y = float(leader["y"])

        position = self._position(ref_y, insert_y, bbox)
        continuity = self._continuity(ref_x, insert_x, bbox)
        confidence = self._confidence_score(position, continuity, bbox)
        return position, continuity, {
            "geometry_confidence": confidence,
            "source": "annotation_heuristic",
        }

    def _position(
        self, ref_y: float, insert_y: float, bbox: dict[str, float]
    ) -> Position:
        ymin, ymax = float(bbox["ymin"]), float(bbox["ymax"])
        height = ymax - ymin
        if height <= 0:
            return "UNKNOWN"
        mid = ymin + height / 2.0
        band = height * _POSITION_BAND_RATIO
        y_vals = [ref_y, insert_y]
        above = sum(1 for y in y_vals if y > mid + band)
        below = sum(1 for y in y_vals if y < mid - band)
        if above >= 1 and below == 0:
            return "TOP"
        if below >= 1 and above == 0:
            return "BOTTOM"
        if ref_y > mid:
            return "TOP"
        if ref_y < mid:
            return "BOTTOM"
        return "UNKNOWN"

    def _continuity(
        self, ref_x: float, insert_x: float, bbox: dict[str, float]
    ) -> Continuity:
        xmin, xmax = float(bbox["xmin"]), float(bbox["xmax"])
        width = xmax - xmin
        if width <= 0:
            return "UNKNOWN"
        xs = [ref_x, insert_x]
        min_rel = min((x - xmin) / width for x in xs)
        max_rel = max((x - xmin) / width for x in xs)
        span = max_rel - min_rel
        if span > (1.0 - 2 * _CONTINUITY_END_RATIO):
            return "CONTINUOUS"
        if min_rel <= _CONTINUITY_END_RATIO or max_rel >= (1.0 - _CONTINUITY_END_RATIO):
            return "PARTIAL"
        if 0.2 <= min_rel and max_rel <= 0.8:
            return "CONTINUOUS"
        return "UNKNOWN"

    def _confidence_score(
        self,
        position: Position,
        continuity: Continuity,
        bbox: dict[str, float],
    ) -> float:
        score = 40.0
        if position != "UNKNOWN":
            score += 25.0
        if continuity != "UNKNOWN":
            score += 25.0
        if bbox:
            score += 10.0
        return min(100.0, score)
