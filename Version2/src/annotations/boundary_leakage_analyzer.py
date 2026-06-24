"""Phase D.1.3.1 — analyze OUTSIDE_REGION annotations for boundary leakage."""

import math
from typing import Any, Dict, List, Literal, Tuple, TypedDict

from loguru import logger

from src.annotations.annotation_region_validator import (
    AnnotationRegionValidator,
    OwnershipRegion,
)

RETAIN_THRESHOLD_MM = 300.0
REASSIGN_CLOSER_RATIO = 0.8

BoundaryType = Literal[
    "LEFT_BOUNDARY",
    "RIGHT_BOUNDARY",
    "TOP_BOUNDARY",
    "BOTTOM_BOUNDARY",
]
LeakageClass = Literal["RETAIN", "REVIEW", "REASSIGN_CANDIDATE"]


class RegionRef(TypedDict):
    beam_mark: str
    occurrence_id: int


class BoundaryLeakageRecord(TypedDict):
    beam_mark: str
    occurrence_id: int
    sketch_id: str
    annotation: str
    x: float
    y: float
    current_region: RegionRef
    nearest_region: RegionRef
    boundary_crossed: BoundaryType
    distance_to_current_region_mm: float
    distance_to_neighbor_region_mm: float
    classification: LeakageClass


class BoundaryLeakageSummary(TypedDict):
    total_outside_annotations: int
    retain: int
    review: int
    reassign_candidate: int


class BoundaryLeakageValidation(TypedDict):
    status: str
    outside_in_d13: int
    analyzed: int
    missing: int


class BoundaryLeakageAnalyzer:
    """Diagnose whether outside annotations belong to a neighboring ownership region."""

    def analyze(
        self,
        region_validation: List[dict[str, Any]],
        ownership: List[dict[str, Any]],
        occurrences: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
        beam_cells: List[dict[str, Any]],
    ) -> Tuple[
        List[BoundaryLeakageRecord],
        BoundaryLeakageSummary,
        BoundaryLeakageValidation,
        Dict[Tuple[str, int], OwnershipRegion],
    ]:
        region_validator = AnnotationRegionValidator()
        regions = region_validator.build_regions(
            ownership, occurrences, sketches, beam_cells
        )

        outside_records = [
            record
            for record in region_validation
            if str(record.get("classification")) == "OUTSIDE_REGION"
        ]

        leakage_records: List[BoundaryLeakageRecord] = []
        for record in outside_records:
            leakage = self._analyze_record(record, regions)
            if leakage is not None:
                leakage_records.append(leakage)

        leakage_records.sort(
            key=lambda item: (
                item["beam_mark"],
                item["occurrence_id"],
                item["sketch_id"],
                -item["y"],
                item["x"],
            )
        )

        summary = self._build_summary(leakage_records)
        validation = self._build_validation(len(outside_records), len(leakage_records))

        logger.info(
            "Boundary leakage: {} outside, {} retain, {} review, {} reassign_candidate",
            summary["total_outside_annotations"],
            summary["retain"],
            summary["review"],
            summary["reassign_candidate"],
        )
        return leakage_records, summary, validation, regions

    def build_report_text(
        self,
        records: List[BoundaryLeakageRecord],
        summary: BoundaryLeakageSummary,
    ) -> str:
        reassign_records = [
            record for record in records if record["classification"] == "REASSIGN_CANDIDATE"
        ]

        lines = [
            "=================================================",
            "Boundary Leakage Report",
            "=================================================",
            "",
            f"Total Outside Annotations: {summary['total_outside_annotations']}",
            "",
            f"Retain: {summary['retain']}",
            f"Review: {summary['review']}",
            f"Reassign Candidate: {summary['reassign_candidate']}",
            "",
        ]

        if reassign_records:
            lines.append("Potential Reassignments")
            lines.append("")
            for record in reassign_records:
                preview = AnnotationRegionValidator._preview_text(record["annotation"])
                current_label = AnnotationRegionValidator.region_label(
                    record["current_region"]["beam_mark"],
                    record["current_region"]["occurrence_id"],
                )
                neighbor_label = AnnotationRegionValidator.region_label(
                    record["nearest_region"]["beam_mark"],
                    record["nearest_region"]["occurrence_id"],
                )
                lines.extend(
                    [
                        record["sketch_id"],
                        preview,
                        "",
                        "Current:",
                        current_label,
                        "",
                        "Suggested:",
                        neighbor_label,
                        "",
                        "Current Distance:",
                        f"{record['distance_to_current_region_mm']:.1f} mm",
                        "",
                        "Neighbor Distance:",
                        f"{record['distance_to_neighbor_region_mm']:.1f} mm",
                        "",
                        "Boundary:",
                        record["boundary_crossed"],
                        "",
                    ]
                )

        lines.append("=================================================")
        return "\n".join(lines) + "\n"

    def _analyze_record(
        self,
        record: dict[str, Any],
        regions: Dict[Tuple[str, int], OwnershipRegion],
    ) -> BoundaryLeakageRecord | None:
        beam_mark = str(record["beam_mark"])
        occurrence_id = int(record["occurrence_id"])
        sketch_id = str(record["sketch_id"])
        annotation = str(record["annotation"])
        x = float(record["x"])
        y = float(record["y"])
        current_key = (beam_mark, occurrence_id)

        current_region = regions.get(current_key)
        if current_region is None:
            logger.warning(
                "Current region missing for {} occurrence {} — skipping",
                beam_mark,
                occurrence_id,
            )
            return None

        current_bbox = self._region_bbox_tuple(current_region)
        distance_current = float(record.get("distance_to_region_mm", 0.0))
        if distance_current == 0.0:
            distance_current = self._distance_to_bbox(x, y, current_bbox)

        nearest_key, distance_neighbor = self._nearest_region(
            x, y, regions, exclude_key=current_key
        )
        if nearest_key is None:
            logger.warning(
                "No neighbor region found for {} {} — skipping",
                beam_mark,
                sketch_id,
            )
            return None

        nearest_region = regions[nearest_key]
        boundary = self._boundary_crossed(x, y, current_bbox)
        classification = self._classify_leakage(distance_current, distance_neighbor)

        return BoundaryLeakageRecord(
            beam_mark=beam_mark,
            occurrence_id=occurrence_id,
            sketch_id=sketch_id,
            annotation=annotation,
            x=round(x, 1),
            y=round(y, 1),
            current_region=RegionRef(
                beam_mark=beam_mark,
                occurrence_id=occurrence_id,
            ),
            nearest_region=RegionRef(
                beam_mark=str(nearest_region["beam_mark"]),
                occurrence_id=int(nearest_region["occurrence_id"]),
            ),
            boundary_crossed=boundary,
            distance_to_current_region_mm=round(distance_current, 1),
            distance_to_neighbor_region_mm=round(distance_neighbor, 1),
            classification=classification,
        )

    def _nearest_region(
        self,
        x: float,
        y: float,
        regions: Dict[Tuple[str, int], OwnershipRegion],
        exclude_key: Tuple[str, int],
    ) -> Tuple[Tuple[str, int] | None, float]:
        best_key: Tuple[str, int] | None = None
        best_distance = float("inf")

        for key, region in regions.items():
            if key == exclude_key:
                continue
            bbox = self._region_bbox_tuple(region)
            distance = self._distance_to_bbox(x, y, bbox)
            if distance < best_distance:
                best_distance = distance
                best_key = key

        if best_key is None:
            return None, 0.0
        return best_key, best_distance

    def _classify_leakage(
        self, distance_current: float, distance_neighbor: float
    ) -> LeakageClass:
        if distance_current <= RETAIN_THRESHOLD_MM:
            return "RETAIN"

        if distance_neighbor < distance_current:
            threshold = distance_current * REASSIGN_CLOSER_RATIO
            if distance_neighbor < threshold:
                return "REASSIGN_CANDIDATE"

        return "REVIEW"

    @staticmethod
    def _boundary_crossed(
        x: float,
        y: float,
        bbox: Tuple[float, float, float, float],
    ) -> BoundaryType:
        xmin, ymin, xmax, ymax = bbox
        dist_left = xmin - x if x < xmin else 0.0
        dist_right = x - xmax if x > xmax else 0.0
        dist_bottom = ymin - y if y < ymin else 0.0
        dist_top = y - ymax if y > ymax else 0.0

        edge_distances: List[Tuple[float, BoundaryType]] = [
            (dist_left, "LEFT_BOUNDARY"),
            (dist_right, "RIGHT_BOUNDARY"),
            (dist_bottom, "BOTTOM_BOUNDARY"),
            (dist_top, "TOP_BOUNDARY"),
        ]
        return max(edge_distances, key=lambda item: item[0])[1]

    @staticmethod
    def _region_bbox_tuple(
        region: OwnershipRegion,
    ) -> Tuple[float, float, float, float]:
        return (
            float(region["xmin"]),
            float(region["ymin"]),
            float(region["xmax"]),
            float(region["ymax"]),
        )

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

    def _build_summary(
        self, records: List[BoundaryLeakageRecord]
    ) -> BoundaryLeakageSummary:
        retain = sum(1 for record in records if record["classification"] == "RETAIN")
        review = sum(1 for record in records if record["classification"] == "REVIEW")
        reassign = sum(
            1 for record in records if record["classification"] == "REASSIGN_CANDIDATE"
        )
        return BoundaryLeakageSummary(
            total_outside_annotations=len(records),
            retain=retain,
            review=review,
            reassign_candidate=reassign,
        )

    def _build_validation(
        self, outside_in_d13: int, analyzed: int
    ) -> BoundaryLeakageValidation:
        missing = outside_in_d13 - analyzed
        status = "PASS" if missing == 0 and outside_in_d13 == analyzed else "FAIL"
        return BoundaryLeakageValidation(
            status=status,
            outside_in_d13=outside_in_d13,
            analyzed=analyzed,
            missing=missing,
        )
