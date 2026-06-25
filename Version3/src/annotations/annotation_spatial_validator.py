"""Phase D.1.2 — geometric validation of annotation-to-sketch spatial ownership."""

import math
from collections import defaultdict
from typing import Any, Dict, List, Tuple, TypedDict

from loguru import logger

BBOX_MARGIN_MM = 300.0


class SpatialValidationRecord(TypedDict):
    beam_mark: str
    sketch_id: str
    annotation: str
    x: float
    y: float
    classification: str
    distance_to_bbox_mm: float


class SpatialValidationSummary(TypedDict):
    total_annotations: int
    inside: int
    near_edge: int
    outside: int
    status: str


class BeamOutsideRatio(TypedDict):
    beam_mark: str
    total: int
    outside: int
    outside_ratio_pct: float


class AnnotationSpatialValidator:
    """Classify whether annotations lie inside, near, or outside sketch bboxes."""

    def validate(
        self,
        annotations_raw: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
    ) -> Tuple[List[SpatialValidationRecord], SpatialValidationSummary]:
        sketch_lookup = {str(sketch["sketch_id"]): sketch for sketch in sketches}
        records: List[SpatialValidationRecord] = []

        for sketch_record in annotations_raw:
            beam_mark = str(sketch_record["beam_mark"])
            sketch_id = str(sketch_record["sketch_id"])
            sketch = sketch_lookup.get(sketch_id)
            if sketch is None:
                logger.warning(
                    "Sketch {} not found — skipping spatial validation",
                    sketch_id,
                )
                continue

            orig_bbox = self._bbox_tuple(sketch["bbox"])
            expanded_bbox = self._expand_bbox(orig_bbox)

            for item in sketch_record.get("texts", []):
                x = float(item["x"])
                y = float(item["y"])
                text = str(item["text"])
                classification = self._classify(x, y, orig_bbox, expanded_bbox)
                distance = self._distance_to_bbox(x, y, orig_bbox)
                records.append(
                    SpatialValidationRecord(
                        beam_mark=beam_mark,
                        sketch_id=sketch_id,
                        annotation=text,
                        x=round(x, 1),
                        y=round(y, 1),
                        classification=classification,
                        distance_to_bbox_mm=round(distance, 1),
                    )
                )

        records.sort(
            key=lambda record: (
                record["beam_mark"],
                record["sketch_id"],
                -record["y"],
                record["x"],
            )
        )
        summary = self._build_summary(records)
        logger.info(
            "Spatial validation: {} inside, {} near_edge, {} outside",
            summary["inside"],
            summary["near_edge"],
            summary["outside"],
        )
        return records, summary

    def beam_outside_ratios(
        self, records: List[SpatialValidationRecord], threshold_pct: float = 25.0
    ) -> List[BeamOutsideRatio]:
        totals: Dict[str, int] = defaultdict(int)
        outside_counts: Dict[str, int] = defaultdict(int)
        for record in records:
            mark = record["beam_mark"]
            totals[mark] += 1
            if record["classification"] == "OUTSIDE":
                outside_counts[mark] += 1

        ratios: List[BeamOutsideRatio] = []
        for mark in sorted(totals.keys(), key=lambda m: m):
            total = totals[mark]
            outside = outside_counts[mark]
            ratio_pct = round((outside / total) * 100.0, 1) if total else 0.0
            if ratio_pct > threshold_pct:
                ratios.append(
                    BeamOutsideRatio(
                        beam_mark=mark,
                        total=total,
                        outside=outside,
                        outside_ratio_pct=ratio_pct,
                    )
                )
        ratios.sort(key=lambda item: -item["outside_ratio_pct"])
        return ratios

    def build_report_text(
        self,
        records: List[SpatialValidationRecord],
        summary: SpatialValidationSummary,
        outside_limit: int = 20,
    ) -> str:
        outside_records = [
            r for r in records if r["classification"] == "OUTSIDE"
        ]
        outside_records.sort(key=lambda r: -r["distance_to_bbox_mm"])

        lines = [
            "==================================================================",
            "Annotation Spatial Ownership Validation",
            "==================================================================",
            "",
            f"Total annotations: {summary['total_annotations']}",
            "",
            f"Inside: {summary['inside']}",
            f"Near Edge: {summary['near_edge']}",
            f"Outside: {summary['outside']}",
            "",
            "---------------------------------------------------------------",
            "Top Outside Annotations",
            "---------------------------------------------------------------",
            "",
            f"{'Beam':<8} {'Sketch':<12} {'Annotation':<32} {'Dist(mm)':>10}",
            "",
        ]
        for record in outside_records[:outside_limit]:
            annotation = self._preview_text(record["annotation"])
            lines.append(
                f"{record['beam_mark']:<8} "
                f"{record['sketch_id']:<12} "
                f"{annotation:<32} "
                f"{record['distance_to_bbox_mm']:>10.1f}"
            )
        lines.append("")
        lines.append(f"Validation status: {summary['status']}")
        return "\n".join(lines) + "\n"

    def _build_summary(
        self, records: List[SpatialValidationRecord]
    ) -> SpatialValidationSummary:
        inside = sum(1 for r in records if r["classification"] == "INSIDE")
        near_edge = sum(1 for r in records if r["classification"] == "NEAR_EDGE")
        outside = sum(1 for r in records if r["classification"] == "OUTSIDE")
        total = len(records)

        outside_ratio = outside / total if total else 0.0
        if outside_ratio <= 0.05:
            status = "PASS"
        elif outside_ratio <= 0.15:
            status = "PASS_WITH_WARNINGS"
        else:
            status = "FAIL"

        return SpatialValidationSummary(
            total_annotations=total,
            inside=inside,
            near_edge=near_edge,
            outside=outside,
            status=status,
        )

    @staticmethod
    def _bbox_tuple(bbox: dict[str, Any]) -> Tuple[float, float, float, float]:
        return (
            float(bbox["xmin"]),
            float(bbox["ymin"]),
            float(bbox["xmax"]),
            float(bbox["ymax"]),
        )

    @staticmethod
    def _expand_bbox(
        bbox: Tuple[float, float, float, float],
    ) -> Tuple[float, float, float, float]:
        xmin, ymin, xmax, ymax = bbox
        return (
            xmin - BBOX_MARGIN_MM,
            ymin - BBOX_MARGIN_MM,
            xmax + BBOX_MARGIN_MM,
            ymax + BBOX_MARGIN_MM,
        )

    @staticmethod
    def _point_in_bbox(
        x: float, y: float, bbox: Tuple[float, float, float, float]
    ) -> bool:
        xmin, ymin, xmax, ymax = bbox
        return xmin <= x <= xmax and ymin <= y <= ymax

    def _classify(
        self,
        x: float,
        y: float,
        orig_bbox: Tuple[float, float, float, float],
        expanded_bbox: Tuple[float, float, float, float],
    ) -> str:
        if self._point_in_bbox(x, y, orig_bbox):
            return "INSIDE"
        if self._point_in_bbox(x, y, expanded_bbox):
            return "NEAR_EDGE"
        return "OUTSIDE"

    @staticmethod
    def _distance_to_bbox(
        x: float, y: float, bbox: Tuple[float, float, float, float]
    ) -> float:
        xmin, ymin, xmax, ymax = bbox
        if xmin <= x <= xmax and ymin <= y <= ymax:
            return 0.0

        dx = xmin - x if x < xmin else (x - xmax if x > xmax else 0.0)
        dy = ymin - y if y < ymin else (y - ymax if y > ymax else 0.0)
        return math.hypot(dx, dy)

    @staticmethod
    def _nearest_point_on_bbox(
        x: float, y: float, bbox: Tuple[float, float, float, float]
    ) -> Tuple[float, float]:
        xmin, ymin, xmax, ymax = bbox
        nx = min(max(x, xmin), xmax)
        ny = min(max(y, ymin), ymax)
        return nx, ny

    @staticmethod
    def _preview_text(text: str) -> str:
        cleaned = text.replace("\\P", " ").replace("\n", " ").strip()
        if cleaned.startswith("\\A1;"):
            cleaned = cleaned[4:]
        if len(cleaned) > 32:
            return cleaned[:29] + "..."
        return cleaned
