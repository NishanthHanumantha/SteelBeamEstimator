"""Orchestrate annotation type classification from reassigned ownership data."""

import math
from collections import defaultdict
from typing import Any, Dict, List, Tuple, TypedDict

from loguru import logger

from src.annotations.annotation_type_classifier import AnnotationTypeClassifier
from src.framing.beam_geometry import beam_mark_sort_key


class ClassifiedAnnotation(TypedDict):
    raw_text: str
    clean_text: str
    annotation_type: str
    x: float
    y: float


class SketchTypeRecord(TypedDict):
    beam_mark: str
    occurrence_id: int
    sketch_id: str
    annotations: List[ClassifiedAnnotation]


class AnnotationTypePipeline:
    """Classify reassigned annotations and group by owning sketch."""

    def classify_all(
        self,
        reassigned: List[dict[str, Any]],
        ownership: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
    ) -> Tuple[List[SketchTypeRecord], List[ClassifiedAnnotation]]:
        sketch_lookup = {str(sketch["sketch_id"]): sketch for sketch in sketches}
        sketches_by_occurrence = self._sketches_by_occurrence(ownership)
        classifier = AnnotationTypeClassifier()

        flat_records: List[ClassifiedAnnotation] = []
        grouped: Dict[Tuple[str, int, str], List[ClassifiedAnnotation]] = defaultdict(
            list
        )

        for occurrence_record in reassigned:
            beam_mark = str(occurrence_record["beam_mark"])
            occurrence_id = int(occurrence_record["occurrence_id"])
            sketch_ids = sketches_by_occurrence.get((beam_mark, occurrence_id), [])

            for item in occurrence_record.get("annotations", []):
                raw_text = str(item["text"])
                x = float(item["x"])
                y = float(item["y"])
                raw, clean, annotation_type = classifier.classify(raw_text)

                if sketch_ids:
                    sketch_id = self._nearest_sketch_id(
                        sketch_ids, sketch_lookup, x, y
                    )
                else:
                    sketch_id = "UNKNOWN"
                    logger.warning(
                        "No sketches for {} occurrence {} — sketch_id UNKNOWN",
                        beam_mark,
                        occurrence_id,
                    )

                classified = ClassifiedAnnotation(
                    raw_text=raw,
                    clean_text=clean,
                    annotation_type=annotation_type,
                    x=round(x, 1),
                    y=round(y, 1),
                )
                flat_records.append(classified)
                grouped[(beam_mark, occurrence_id, sketch_id)].append(classified)

        sketch_records: List[SketchTypeRecord] = []
        for key in sorted(
            grouped.keys(),
            key=lambda item: (
                beam_mark_sort_key(item[0]),
                item[1],
                item[2],
            ),
        ):
            beam_mark, occurrence_id, sketch_id = key
            annotations = grouped[key]
            annotations.sort(key=lambda item: (-item["y"], item["x"], item["clean_text"]))
            sketch_records.append(
                SketchTypeRecord(
                    beam_mark=beam_mark,
                    occurrence_id=occurrence_id,
                    sketch_id=sketch_id,
                    annotations=annotations,
                )
            )

        logger.info("Classified {} annotation(s)", len(flat_records))
        return sketch_records, flat_records

    @staticmethod
    def _sketches_by_occurrence(
        ownership: List[dict[str, Any]],
    ) -> Dict[Tuple[str, int], List[str]]:
        mapping: Dict[Tuple[str, int], List[str]] = defaultdict(list)
        for record in ownership:
            mark = str(record["beam_mark"])
            occurrence_id = int(record["occurrence_id"])
            key = (mark, occurrence_id)
            for item in record.get("owned_sketches", []):
                sketch_id = (
                    str(item["sketch_id"]) if isinstance(item, dict) else str(item)
                )
                mapping[key].append(sketch_id)
        return mapping

    @staticmethod
    def _nearest_sketch_id(
        sketch_ids: List[str],
        sketch_lookup: Dict[str, dict[str, Any]],
        x: float,
        y: float,
    ) -> str:
        best_id = sketch_ids[0]
        best_dist = float("inf")
        for sketch_id in sketch_ids:
            sketch = sketch_lookup.get(sketch_id)
            if sketch is None:
                continue
            bbox = sketch["bbox"]
            cx = (float(bbox["xmin"]) + float(bbox["xmax"])) / 2.0
            cy = (float(bbox["ymin"]) + float(bbox["ymax"])) / 2.0
            dist = math.hypot(cx - x, cy - y)
            if dist < best_dist:
                best_dist = dist
                best_id = sketch_id
        return best_id
