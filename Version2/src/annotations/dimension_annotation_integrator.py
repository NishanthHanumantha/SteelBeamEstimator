"""Phase D.1.7 — integrate DIMENSION annotations into ownership pipeline."""

import copy
import math
import re
from collections import defaultdict
from typing import Any, Dict, List, Literal, Tuple, TypedDict

from loguru import logger

from src.annotations.annotation_region_validator import (
    REGION_EDGE_MARGIN_MM,
    AnnotationRegionValidator,
    OwnershipRegion,
)
from src.annotations.boundary_leakage_analyzer import (
    REASSIGN_CLOSER_RATIO,
    RETAIN_THRESHOLD_MM,
)
from src.annotations.dimension_annotation_extractor import DimensionAnnotation
from src.framing.beam_geometry import beam_mark_sort_key
from src.parser.dxf_flattener import flatten_entities
from src.parser.dxf_reader import DxfReader

OwnershipSource = Literal["INSIDE_REGION", "NEAR_REGION_EDGE", "REASSIGNED", "ORIGINAL"]


class ExtendedAnnotation(TypedDict, total=False):
    entity_type: str
    text: str
    x: float
    y: float
    layer: str
    ownership_source: str
    previous_owner: Dict[str, Any]


class OccurrenceExtendedRecord(TypedDict):
    beam_mark: str
    occurrence_id: int
    annotations: List[ExtendedAnnotation]


class DimensionAssignment(TypedDict):
    dimension: DimensionAnnotation
    beam_mark: str
    occurrence_id: int
    ownership_source: OwnershipSource
    assigned: bool


class IntegrationResult(TypedDict):
    extended_records: List[OccurrenceExtendedRecord]
    dimension_assignments: List[DimensionAssignment]


_STIRRUP_PATTERN = re.compile(r"@|C/C", re.IGNORECASE)
_ANCHORAGE_PATTERN = re.compile(r"\bLD\b", re.IGNORECASE)
_NUMERIC_DIMENSION_PATTERN = re.compile(r"^\d+$")
_MATCH_TOLERANCE_MM = 1.0


class DimensionAnnotationIntegrator:
    """Merge reassigned TEXT/MTEXT with DIMENSION entities under occurrence ownership."""

    def integrate(
        self,
        dxf_path: str,
        reassigned: List[dict[str, Any]],
        dimensions: List[DimensionAnnotation],
        ownership: List[dict[str, Any]],
        occurrences: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
        beam_cells: List[dict[str, Any]],
    ) -> IntegrationResult:
        regions = AnnotationRegionValidator().build_regions(
            ownership, occurrences, sketches, beam_cells
        )
        text_entity_types = self._load_text_entity_types(dxf_path)

        extended = self._build_base_extended(reassigned, text_entity_types)
        assignments = self._assign_dimensions(dimensions, regions)

        for assignment in assignments:
            if not assignment["assigned"]:
                continue
            key = (assignment["beam_mark"], assignment["occurrence_id"])
            annotation: ExtendedAnnotation = {
                "entity_type": "DIMENSION",
                "text": assignment["dimension"]["text"],
                "x": assignment["dimension"]["x"],
                "y": assignment["dimension"]["y"],
                "layer": assignment["dimension"]["layer"],
                "ownership_source": assignment["ownership_source"],
            }
            extended.setdefault(key, []).append(annotation)

        extended_records = self._to_occurrence_records(extended)
        logger.info(
            "Integrated {} DIMENSION annotation(s) into extended ownership output",
            sum(1 for item in assignments if item["assigned"]),
        )
        return IntegrationResult(
            extended_records=extended_records,
            dimension_assignments=assignments,
        )

    def _build_base_extended(
        self,
        reassigned: List[dict[str, Any]],
        text_entity_types: Dict[Tuple[str, float, float], str],
    ) -> Dict[Tuple[str, int], List[ExtendedAnnotation]]:
        grouped: Dict[Tuple[str, int], List[ExtendedAnnotation]] = defaultdict(list)

        for occurrence_record in reassigned:
            beam_mark = str(occurrence_record["beam_mark"])
            occurrence_id = int(occurrence_record["occurrence_id"])
            key = (beam_mark, occurrence_id)

            for item in occurrence_record.get("annotations", []):
                text = str(item["text"])
                x = round(float(item["x"]), 1)
                y = round(float(item["y"]), 1)
                entity_type = self._match_entity_type(text_entity_types, text, x, y)

                annotation: ExtendedAnnotation = {
                    "entity_type": entity_type,
                    "text": text,
                    "x": x,
                    "y": y,
                }
                if "ownership_source" in item:
                    annotation["ownership_source"] = str(item["ownership_source"])
                if "previous_owner" in item:
                    annotation["previous_owner"] = copy.deepcopy(item["previous_owner"])

                grouped[key].append(annotation)

        return grouped

    def _assign_dimensions(
        self,
        dimensions: List[DimensionAnnotation],
        regions: Dict[Tuple[str, int], OwnershipRegion],
    ) -> List[DimensionAssignment]:
        region_validator = AnnotationRegionValidator()
        assignments: List[DimensionAssignment] = []

        for dimension in dimensions:
            x = float(dimension["x"])
            y = float(dimension["y"])
            owner_key, source, assigned = self._assign_owner(
                x,
                y,
                regions,
                region_validator,
            )
            if owner_key is None or not assigned:
                assignments.append(
                    DimensionAssignment(
                        dimension=dimension,
                        beam_mark="",
                        occurrence_id=0,
                        ownership_source="REASSIGNED",
                        assigned=False,
                    )
                )
                continue

            beam_mark, occurrence_id = owner_key
            assignments.append(
                DimensionAssignment(
                    dimension=dimension,
                    beam_mark=beam_mark,
                    occurrence_id=occurrence_id,
                    ownership_source=source,
                    assigned=True,
                )
            )

        return assignments

    def _assign_owner(
        self,
        x: float,
        y: float,
        regions: Dict[Tuple[str, int], OwnershipRegion],
        region_validator: AnnotationRegionValidator,
    ) -> Tuple[Tuple[str, int] | None, OwnershipSource, bool]:
        inside_keys: List[Tuple[str, int]] = []
        near_keys: List[Tuple[str, int]] = []

        for key, region in regions.items():
            bbox = region_validator._region_bbox_tuple(region)
            expanded = region_validator._expand_bbox(bbox, REGION_EDGE_MARGIN_MM)
            classification = region_validator._classify(x, y, bbox, expanded)
            if classification == "INSIDE_REGION":
                inside_keys.append(key)
            elif classification == "NEAR_REGION_EDGE":
                near_keys.append(key)

        if inside_keys:
            owner = self._nearest_region_center(x, y, inside_keys, regions)
            return owner, "INSIDE_REGION", True

        if near_keys:
            owner = self._nearest_region_center(x, y, near_keys, regions)
            return owner, "NEAR_REGION_EDGE", True

        nearest_key, nearest_distance = self._nearest_region(x, y, regions)
        if nearest_key is None:
            return None, "REASSIGNED", False

        nearest_region = regions[nearest_key]
        nearest_bbox = region_validator._region_bbox_tuple(nearest_region)
        expanded = region_validator._expand_bbox(nearest_bbox, REGION_EDGE_MARGIN_MM)
        if region_validator._point_in_bbox(x, y, expanded):
            return nearest_key, "NEAR_REGION_EDGE", True

        if nearest_distance <= RETAIN_THRESHOLD_MM:
            return nearest_key, "REASSIGNED", True

        second_key, second_distance = self._nearest_region(
            x, y, regions, exclude_key=nearest_key
        )
        if second_key is not None and second_distance < nearest_distance:
            threshold = nearest_distance * REASSIGN_CLOSER_RATIO
            if second_distance < threshold:
                return second_key, "REASSIGNED", True

        return None, "REASSIGNED", False

    @staticmethod
    def _nearest_region(
        x: float,
        y: float,
        regions: Dict[Tuple[str, int], OwnershipRegion],
        exclude_key: Tuple[str, int] | None = None,
    ) -> Tuple[Tuple[str, int] | None, float]:
        best_key: Tuple[str, int] | None = None
        best_distance = float("inf")

        for key, region in regions.items():
            if exclude_key is not None and key == exclude_key:
                continue
            bbox = (
                float(region["xmin"]),
                float(region["ymin"]),
                float(region["xmax"]),
                float(region["ymax"]),
            )
            distance = AnnotationRegionValidator._distance_to_bbox(x, y, bbox)
            if distance < best_distance:
                best_distance = distance
                best_key = key

        if best_key is None:
            return None, 0.0
        return best_key, best_distance

    @staticmethod
    def _nearest_region_center(
        x: float,
        y: float,
        keys: List[Tuple[str, int]],
        regions: Dict[Tuple[str, int], OwnershipRegion],
    ) -> Tuple[str, int]:
        best_key = keys[0]
        best_dist = float("inf")
        for key in keys:
            region = regions[key]
            dist = math.hypot(x - float(region["center_x"]), y - float(region["center_y"]))
            if dist < best_dist:
                best_dist = dist
                best_key = key
        return best_key

    def _load_text_entity_types(self, dxf_path: str) -> Dict[Tuple[str, float, float], str]:
        doc = DxfReader(dxf_path).read()
        flat = flatten_entities(doc.modelspace())
        mapping: Dict[Tuple[str, float, float], str] = {}

        for entity in flat:
            entity_type = entity.dxftype()
            if entity_type not in {"TEXT", "MTEXT"}:
                continue
            if entity_type == "TEXT":
                text = str(entity.dxf.text)
            else:
                text = str(entity.text)
            insert = entity.dxf.insert
            x = round(float(insert.x), 1)
            y = round(float(insert.y), 1)
            mapping[(text, x, y)] = entity_type

        return mapping

    def _match_entity_type(
        self,
        text_entity_types: Dict[Tuple[str, float, float], str],
        text: str,
        x: float,
        y: float,
    ) -> str:
        direct = text_entity_types.get((text, x, y))
        if direct is not None:
            return direct

        for (candidate_text, candidate_x, candidate_y), entity_type in text_entity_types.items():
            if candidate_text != text:
                continue
            if math.hypot(x - candidate_x, y - candidate_y) <= _MATCH_TOLERANCE_MM:
                return entity_type

        return "TEXT"

    def _to_occurrence_records(
        self,
        grouped: Dict[Tuple[str, int], List[ExtendedAnnotation]],
    ) -> List[OccurrenceExtendedRecord]:
        records: List[OccurrenceExtendedRecord] = []
        for key in sorted(
            grouped.keys(),
            key=lambda item: (beam_mark_sort_key(item[0]), item[1]),
        ):
            beam_mark, occurrence_id = key
            annotations = grouped[key]
            annotations.sort(key=lambda item: (-item["y"], item["x"], item["text"]))
            records.append(
                OccurrenceExtendedRecord(
                    beam_mark=beam_mark,
                    occurrence_id=occurrence_id,
                    annotations=annotations,
                )
            )
        return records

    @staticmethod
    def classify_dimension_category(text: str) -> str:
        normalized = text.strip()
        upper = normalized.upper()
        if _STIRRUP_PATTERN.search(normalized):
            return "STIRRUP"
        if _ANCHORAGE_PATTERN.search(upper) or upper == "LD":
            return "ANCHORAGE"
        if _NUMERIC_DIMENSION_PATTERN.match(normalized):
            return "NUMERIC_DIMENSION"
        return "OTHER"
