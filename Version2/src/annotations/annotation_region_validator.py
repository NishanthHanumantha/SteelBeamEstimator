"""Phase D.1.3 — validate annotations against header-occurrence ownership regions."""

import math
from collections import defaultdict
from typing import Any, Dict, List, Tuple, TypedDict

from loguru import logger

from src.annotations.raw_annotation_extractor import (
    BBOX_MARGIN_MM,
    ROW_EDGE_MARGIN_MM,
    RawAnnotationExtractor,
)

REGION_EDGE_MARGIN_MM = 300.0


class OwnershipRegion(TypedDict):
    beam_mark: str
    occurrence_id: int
    xmin: float
    xmax: float
    ymin: float
    ymax: float
    center_x: float
    center_y: float


class RegionValidationRecord(TypedDict):
    beam_mark: str
    occurrence_id: int
    sketch_id: str
    annotation: str
    x: float
    y: float
    classification: str
    distance_to_region_mm: float


class RegionValidationSummary(TypedDict):
    total_annotations: int
    inside_region: int
    near_region_edge: int
    outside_region: int
    status: str


class AnnotationRegionValidator:
    """Classify annotations against ownership column regions per header occurrence."""

    def build_regions(
        self,
        ownership: List[dict[str, Any]],
        occurrences: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
        beam_cells: List[dict[str, Any]],
    ) -> Dict[Tuple[str, int], OwnershipRegion]:
        sketch_lookup = {str(sketch["sketch_id"]): sketch for sketch in sketches}
        occurrence_lookup = {
            (str(occ["beam_mark"]), int(occ["occurrence_id"])): occ
            for occ in occurrences
        }
        column_bounds = self._occurrence_column_bounds(occurrences, beam_cells)
        extractor = RawAnnotationExtractor()
        owned_refs = extractor._owned_sketch_refs(ownership)
        occurrence_groups = extractor._group_by_occurrence(owned_refs, sketch_lookup)

        regions: Dict[Tuple[str, int], OwnershipRegion] = {}
        for key, col_bounds in column_bounds.items():
            mark, occurrence_id = key
            occurrence = occurrence_lookup.get(key)
            contexts = occurrence_groups.get(key)
            if occurrence is None or not contexts:
                logger.warning(
                    "Occurrence {} occurrence_id={} missing context — skipping region",
                    mark,
                    occurrence_id,
                )
                continue

            col_xmin, col_xmax = col_bounds
            ymin, ymax = self._occurrence_vertical_bounds(contexts)
            header_y = float(occurrence["y"])

            regions[key] = OwnershipRegion(
                beam_mark=mark,
                occurrence_id=occurrence_id,
                xmin=round(col_xmin, 3),
                xmax=round(col_xmax, 3),
                ymin=round(ymin, 3),
                ymax=round(ymax, 3),
                center_x=round(float(occurrence["x"]), 3),
                center_y=round(header_y, 3),
            )

        logger.info("Built {} ownership region(s)", len(regions))
        return regions

    def validate(
        self,
        annotations_raw: List[dict[str, Any]],
        ownership: List[dict[str, Any]],
        occurrences: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
        beam_cells: List[dict[str, Any]],
    ) -> Tuple[
        List[RegionValidationRecord],
        RegionValidationSummary,
        Dict[Tuple[str, int], OwnershipRegion],
    ]:
        regions = self.build_regions(ownership, occurrences, sketches, beam_cells)
        records: List[RegionValidationRecord] = []

        for sketch_record in annotations_raw:
            beam_mark = str(sketch_record["beam_mark"])
            occurrence_id = int(sketch_record["occurrence_id"])
            sketch_id = str(sketch_record["sketch_id"])
            key = (beam_mark, occurrence_id)
            region = regions.get(key)
            if region is None:
                logger.warning(
                    "No ownership region for {} occurrence {} — skipping annotations",
                    beam_mark,
                    occurrence_id,
                )
                continue

            region_bbox = self._region_bbox_tuple(region)
            expanded_bbox = self._expand_bbox(region_bbox, REGION_EDGE_MARGIN_MM)

            for item in sketch_record.get("texts", []):
                x = float(item["x"])
                y = float(item["y"])
                text = str(item["text"])
                classification = self._classify(x, y, region_bbox, expanded_bbox)
                distance = self._distance_to_bbox(x, y, region_bbox)
                records.append(
                    RegionValidationRecord(
                        beam_mark=beam_mark,
                        occurrence_id=occurrence_id,
                        sketch_id=sketch_id,
                        annotation=text,
                        x=round(x, 1),
                        y=round(y, 1),
                        classification=classification,
                        distance_to_region_mm=round(distance, 1),
                    )
                )

        records.sort(
            key=lambda record: (
                record["beam_mark"],
                record["occurrence_id"],
                record["sketch_id"],
                -record["y"],
                record["x"],
            )
        )
        summary = self._build_summary(records)
        logger.info(
            "Region validation: {} inside, {} near_edge, {} outside",
            summary["inside_region"],
            summary["near_region_edge"],
            summary["outside_region"],
        )
        return records, summary, regions

    def build_report_text(
        self,
        records: List[RegionValidationRecord],
        summary: RegionValidationSummary,
        outside_limit: int = 10,
    ) -> str:
        outside_records = [
            record for record in records if record["classification"] == "OUTSIDE_REGION"
        ]
        outside_records.sort(key=lambda record: -record["distance_to_region_mm"])

        lines = [
            "==============================================================",
            "Annotation Ownership Region Validation",
            "==============================================================",
            "",
            f"Total annotations: {summary['total_annotations']}",
            "",
            f"Inside Region: {summary['inside_region']}",
            f"Near Edge: {summary['near_region_edge']}",
            f"Outside Region: {summary['outside_region']}",
            "",
            f"Validation Status: {summary['status']}",
            "",
            "Top Outside Annotations",
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
                f"{record['distance_to_region_mm']:>10.1f}"
            )
        lines.append("")
        lines.append("==============================================================")
        return "\n".join(lines) + "\n"

    def _occurrence_column_bounds(
        self,
        occurrences: List[dict[str, Any]],
        beam_cells: List[dict[str, Any]],
    ) -> Dict[Tuple[str, int], Tuple[float, float]]:
        """Horizontal ownership bands: midpoint column bounds per header row."""
        beam_row = {
            str(cell["beam_mark"]): int(cell["row_id"]) for cell in beam_cells
        }
        rows: Dict[int, List[dict[str, Any]]] = defaultdict(list)
        for occurrence in occurrences:
            row_id = beam_row.get(str(occurrence["beam_mark"]))
            if row_id is not None:
                rows[row_id].append(occurrence)

        bounds: Dict[Tuple[str, int], Tuple[float, float]] = {}
        for row in rows.values():
            sorted_row = sorted(row, key=lambda occ: float(occ["x"]))
            for index, occurrence in enumerate(sorted_row):
                if index == 0:
                    xmin = float(occurrence["x"]) - ROW_EDGE_MARGIN_MM
                else:
                    xmin = (
                        float(sorted_row[index - 1]["x"]) + float(occurrence["x"])
                    ) / 2.0

                if index == len(sorted_row) - 1:
                    xmax = float(occurrence["x"]) + ROW_EDGE_MARGIN_MM
                else:
                    xmax = (
                        float(occurrence["x"]) + float(sorted_row[index + 1]["x"])
                    ) / 2.0

                key = (str(occurrence["beam_mark"]), int(occurrence["occurrence_id"]))
                bounds[key] = (xmin, xmax)

        return bounds

    @staticmethod
    def _occurrence_vertical_bounds(
        contexts: List[dict[str, Any]],
    ) -> Tuple[float, float]:
        """Vertical extent aligned with Phase D.1 occurrence search logic."""
        sketch_ymin = min(float(ctx["sketch"]["bbox"]["ymin"]) for ctx in contexts)
        sketch_ymax = max(float(ctx["sketch"]["bbox"]["ymax"]) for ctx in contexts)
        header_y = min(
            float(ctx["sketch"].get("header_y", sketch_ymin)) for ctx in contexts
        )
        ymin = min(sketch_ymin - BBOX_MARGIN_MM, header_y - BBOX_MARGIN_MM)
        ymax = sketch_ymax + BBOX_MARGIN_MM
        return ymin, ymax

    def _build_summary(
        self, records: List[RegionValidationRecord]
    ) -> RegionValidationSummary:
        inside = sum(
            1 for record in records if record["classification"] == "INSIDE_REGION"
        )
        near_edge = sum(
            1
            for record in records
            if record["classification"] == "NEAR_REGION_EDGE"
        )
        outside = sum(
            1 for record in records if record["classification"] == "OUTSIDE_REGION"
        )
        total = len(records)

        outside_ratio = outside / total if total else 0.0
        status = "PASS" if outside_ratio <= 0.10 else "FAIL"

        return RegionValidationSummary(
            total_annotations=total,
            inside_region=inside,
            near_region_edge=near_edge,
            outside_region=outside,
            status=status,
        )

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
    def _expand_bbox(
        bbox: Tuple[float, float, float, float], margin: float
    ) -> Tuple[float, float, float, float]:
        xmin, ymin, xmax, ymax = bbox
        return (xmin - margin, ymin - margin, xmax + margin, ymax + margin)

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
        region_bbox: Tuple[float, float, float, float],
        expanded_bbox: Tuple[float, float, float, float],
    ) -> str:
        if self._point_in_bbox(x, y, region_bbox):
            return "INSIDE_REGION"
        if self._point_in_bbox(x, y, expanded_bbox):
            return "NEAR_REGION_EDGE"
        return "OUTSIDE_REGION"

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
    def _preview_text(text: str) -> str:
        cleaned = text.replace("\\P", " ").replace("\n", " ").strip()
        if cleaned.startswith("\\A1;"):
            cleaned = cleaned[4:]
        if len(cleaned) > 32:
            return cleaned[:29] + "..."
        return cleaned

    @staticmethod
    def region_label(beam_mark: str, occurrence_id: int) -> str:
        return f"{beam_mark}_H{occurrence_id}"
