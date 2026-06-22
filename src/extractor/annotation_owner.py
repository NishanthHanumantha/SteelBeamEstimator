"""Assign reinforcement annotations to beam sketches by ownership score."""

import re
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from src.extractor.detail_text_filter import TextAnnotation, dedupe_annotations, SIDE_FACE_PATTERN

Bbox = Tuple[float, float, float, float]
DIMENSION_OWNERSHIP_PATTERN = re.compile(
    r"^Ld(\+10db)?$|^1900$|^2150$|^500$|^499$",
    re.IGNORECASE,
)
LONGITUDINAL_BAR_PATTERN = re.compile(r"\d+-Y\d+", re.IGNORECASE)
STIRRUP_PATTERN = re.compile(r"2L-Y", re.IGNORECASE)


@dataclass(frozen=True)
class SketchTarget:
    beam_mark: str
    center_x: float
    center_y: float
    expanded_bbox: Bbox
    header: dict


def _point_in_bbox(x: float, y: float, bbox: Bbox) -> bool:
    xmin, ymin, xmax, ymax = bbox
    return xmin <= x <= xmax and ymin <= y <= ymax


def ownership_score(text_x: float, text_y: float, center_x: float, center_y: float) -> float:
    return abs(text_x - center_x) + 0.5 * abs(text_y - center_y)


def uses_nearest_sketch_only(text: str) -> bool:
    if SIDE_FACE_PATTERN.search(text):
        return True
    if DIMENSION_OWNERSHIP_PATTERN.search(text.strip()):
        return True
    return False


def _best_sketch_target(
    text_x: float,
    text_y: float,
    sketches: Sequence[SketchTarget],
) -> SketchTarget | None:
    best: SketchTarget | None = None
    best_score = float("inf")

    for sketch in sketches:
        score = ownership_score(text_x, text_y, sketch.center_x, sketch.center_y)
        if score < best_score:
            best_score = score
            best = sketch

    return best


def assign_annotations(
    annotations: List[TextAnnotation],
    sketches: List[SketchTarget],
) -> dict[str, List[TextAnnotation]]:
    if not sketches:
        return {}

    assigned: dict[str, List[TextAnnotation]] = {
        sketch.beam_mark: [] for sketch in sketches
    }

    for annotation in annotations:
        text_x, text_y = annotation["x"], annotation["y"]
        text = annotation["text"]

        if uses_nearest_sketch_only(text):
            best = _best_sketch_target(text_x, text_y, sketches)
        else:
            in_bbox = [
                sketch
                for sketch in sketches
                if _point_in_bbox(text_x, text_y, sketch.expanded_bbox)
            ]
            best = _best_sketch_target(text_x, text_y, in_bbox)

        if best is not None:
            assigned[best.beam_mark].append(annotation)

    for mark in assigned:
        assigned[mark] = dedupe_annotations(assigned[mark])

    return assigned


def is_detail_complete(texts: List[str]) -> bool:
    has_longitudinal = any(LONGITUDINAL_BAR_PATTERN.search(text) for text in texts)
    has_stirrup = any(STIRRUP_PATTERN.search(text) for text in texts)
    return has_longitudinal and has_stirrup
