"""Phase D.1.7B — filter engineering annotations from extended classified dataset."""

import math
import re
from typing import Any, Dict, List, Literal, Optional, Tuple, TypedDict

from loguru import logger

from src.framing.beam_geometry import beam_mark_sort_key

EngineeringSource = Literal["TEXT_MTEXT", "DIMENSION_OVERRIDE"]
Bucket = Literal["engineering", "geometry", "rejected"]

ENGINEERING_ANNOTATION_TYPES = frozenset(
    {"BAR", "STIRRUP", "ANCHORAGE", "SIDE_FACE_REINF"}
)
GEOMETRY_QA_VALUES = frozenset({"500", "1900", "2150"})
_MATCH_TOLERANCE_MM = 1.0
_NUMERIC_PATTERN = re.compile(r"^\d+$")


class FilteredAnnotation(TypedDict, total=False):
    beam_mark: str
    occurrence_id: int
    sketch_id: str
    text: str
    clean_text: str
    entity_type: str
    annotation_type: str
    x: float
    y: float
    layer: str
    ownership_source: str
    engineering_source: EngineeringSource
    rejection_reason: str


class SketchFilterRecord(TypedDict):
    beam_mark: str
    occurrence_id: int
    sketch_id: str
    annotations: List[FilteredAnnotation]


class FilterSummary(TypedDict):
    total_input_annotations: int
    engineering_annotations: int
    geometry_dimensions: int
    rejected_measurements: int
    count_by_type: Dict[str, int]


class FilterResult(TypedDict):
    engineering: List[SketchFilterRecord]
    geometry: List[SketchFilterRecord]
    rejected: List[FilteredAnnotation]
    summary: FilterSummary
    report_text: str


class EngineeringAnnotationFilter:
    """Separate engineering callouts from AutoCAD geometric dimension values."""

    def filter(
        self,
        types_extended: List[dict[str, Any]],
        annotations_extended: List[dict[str, Any]],
        dimension_source_audit: List[dict[str, Any]],
    ) -> FilterResult:
        metadata_lookup = self._build_metadata_lookup(annotations_extended)
        source_lookup = self._build_dimension_source_lookup(dimension_source_audit)

        engineering_records: List[SketchFilterRecord] = []
        geometry_records: List[SketchFilterRecord] = []
        rejected: List[FilteredAnnotation] = []

        total_input = 0
        engineering_by_type: Dict[str, int] = {
            "BAR": 0,
            "STIRRUP": 0,
            "ANCHORAGE": 0,
            "SIDE_FACE_REINF": 0,
        }

        for sketch_record in types_extended:
            beam_mark = str(sketch_record["beam_mark"])
            occurrence_id = int(sketch_record["occurrence_id"])
            sketch_id = str(sketch_record["sketch_id"])

            eng_items: List[FilteredAnnotation] = []
            geo_items: List[FilteredAnnotation] = []

            for item in sketch_record.get("annotations", []):
                total_input += 1
                bucket, filtered = self._classify_item(
                    beam_mark,
                    occurrence_id,
                    sketch_id,
                    item,
                    metadata_lookup,
                    source_lookup,
                )
                if bucket == "engineering" and filtered is not None:
                    eng_items.append(filtered)
                    ann_type = str(filtered["annotation_type"])
                    if ann_type in engineering_by_type:
                        engineering_by_type[ann_type] += 1
                elif bucket == "geometry" and filtered is not None:
                    geo_items.append(filtered)
                elif bucket == "rejected" and filtered is not None:
                    rejected.append(filtered)

            if eng_items:
                engineering_records.append(
                    SketchFilterRecord(
                        beam_mark=beam_mark,
                        occurrence_id=occurrence_id,
                        sketch_id=sketch_id,
                        annotations=eng_items,
                    )
                )
            if geo_items:
                geometry_records.append(
                    SketchFilterRecord(
                        beam_mark=beam_mark,
                        occurrence_id=occurrence_id,
                        sketch_id=sketch_id,
                        annotations=geo_items,
                    )
                )

        engineering_records.sort(
            key=lambda r: (
                beam_mark_sort_key(r["beam_mark"]),
                r["occurrence_id"],
                r["sketch_id"],
            )
        )
        geometry_records.sort(
            key=lambda r: (
                beam_mark_sort_key(r["beam_mark"]),
                r["occurrence_id"],
                r["sketch_id"],
            )
        )

        engineering_count = sum(
            len(r["annotations"]) for r in engineering_records
        )
        geometry_count = sum(len(r["annotations"]) for r in geometry_records)

        summary = FilterSummary(
            total_input_annotations=total_input,
            engineering_annotations=engineering_count,
            geometry_dimensions=geometry_count,
            rejected_measurements=len(rejected),
            count_by_type=engineering_by_type,
        )
        report_text = self._build_report_text(summary)

        logger.info(
            "Engineering filter: {} input, {} engineering, {} geometry, {} rejected",
            total_input,
            engineering_count,
            geometry_count,
            len(rejected),
        )
        return FilterResult(
            engineering=engineering_records,
            geometry=geometry_records,
            rejected=rejected,
            summary=summary,
            report_text=report_text,
        )

    def _classify_item(
        self,
        beam_mark: str,
        occurrence_id: int,
        sketch_id: str,
        item: dict[str, Any],
        metadata_lookup: Dict[Tuple[str, int, float, float, str], dict[str, Any]],
        source_lookup: Dict[Tuple[float, float, str, str], str],
    ) -> Tuple[Bucket, Optional[FilteredAnnotation]]:
        raw_text = str(item.get("raw_text", item.get("text", "")))
        clean_text = str(item["clean_text"])
        annotation_type = str(item["annotation_type"])
        x = round(float(item["x"]), 1)
        y = round(float(item["y"]), 1)

        meta = self._find_metadata(
            metadata_lookup,
            beam_mark,
            occurrence_id,
            x,
            y,
            raw_text,
            clean_text,
        )
        entity_type = str(meta.get("entity_type", "TEXT"))
        layer = str(meta.get("layer", ""))
        ownership_source = meta.get("ownership_source")

        base: FilteredAnnotation = {
            "beam_mark": beam_mark,
            "occurrence_id": occurrence_id,
            "sketch_id": sketch_id,
            "text": raw_text,
            "clean_text": clean_text,
            "entity_type": entity_type,
            "annotation_type": annotation_type,
            "x": x,
            "y": y,
        }
        if layer:
            base["layer"] = layer
        if ownership_source is not None:
            base["ownership_source"] = str(ownership_source)

        if entity_type in ("TEXT", "MTEXT"):
            if annotation_type not in ENGINEERING_ANNOTATION_TYPES:
                base["rejection_reason"] = f"non_engineering_type:{annotation_type}"
                return "rejected", base
            base["engineering_source"] = "TEXT_MTEXT"
            return "engineering", base

        if entity_type == "DIMENSION":
            source_type = self._dimension_source_type(
                source_lookup, x, y, clean_text, layer
            )
            if source_type == "MEASUREMENT_VALUE":
                if clean_text in GEOMETRY_QA_VALUES:
                    base["rejection_reason"] = "geometry_qa_measurement"
                    return "geometry", base
                base["rejection_reason"] = "autocad_measurement_value"
                return "rejected", base

            if source_type == "ENGINEERING_TEXT":
                if annotation_type in ENGINEERING_ANNOTATION_TYPES:
                    base["engineering_source"] = "DIMENSION_OVERRIDE"
                    return "engineering", base
                base["rejection_reason"] = f"non_engineering_dimension:{annotation_type}"
                return "rejected", base

            if annotation_type in ("STIRRUP", "ANCHORAGE", "SIDE_FACE_REINF"):
                base["engineering_source"] = "DIMENSION_OVERRIDE"
                return "engineering", base

            if annotation_type == "DIMENSION" and clean_text in GEOMETRY_QA_VALUES:
                base["rejection_reason"] = "geometry_qa_measurement"
                return "geometry", base

            if _NUMERIC_PATTERN.match(clean_text):
                base["rejection_reason"] = "autocad_measurement_value"
                return "rejected", base

            base["rejection_reason"] = f"unclassified_dimension:{annotation_type}"
            return "rejected", base

        base["rejection_reason"] = f"unsupported_entity:{entity_type}"
        return "rejected", base

    def _build_metadata_lookup(
        self, annotations_extended: List[dict[str, Any]]
    ) -> Dict[Tuple[str, int, float, float, str], dict[str, Any]]:
        lookup: Dict[Tuple[str, int, float, float, str], dict[str, Any]] = {}
        for occurrence_record in annotations_extended:
            beam_mark = str(occurrence_record["beam_mark"])
            occurrence_id = int(occurrence_record["occurrence_id"])
            for annotation in occurrence_record.get("annotations", []):
                text = str(annotation["text"])
                x = round(float(annotation["x"]), 1)
                y = round(float(annotation["y"]), 1)
                key = (beam_mark, occurrence_id, x, y, text)
                lookup[key] = annotation
        return lookup

    def _find_metadata(
        self,
        lookup: Dict[Tuple[str, int, float, float, str], dict[str, Any]],
        beam_mark: str,
        occurrence_id: int,
        x: float,
        y: float,
        raw_text: str,
        clean_text: str,
    ) -> dict[str, Any]:
        direct = lookup.get((beam_mark, occurrence_id, x, y, raw_text))
        if direct is not None:
            return direct

        for (mark, occ_id, ax, ay, text), meta in lookup.items():
            if mark != beam_mark or occ_id != occurrence_id:
                continue
            if text != raw_text and text != clean_text:
                continue
            if math.hypot(x - ax, y - ay) <= _MATCH_TOLERANCE_MM:
                return meta

        return {"entity_type": "TEXT"}

    def _build_dimension_source_lookup(
        self, dimension_source_audit: List[dict[str, Any]]
    ) -> Dict[Tuple[float, float, str, str], str]:
        lookup: Dict[Tuple[float, float, str, str], str] = {}
        for record in dimension_source_audit:
            key = (
                round(float(record["x"]), 1),
                round(float(record["y"]), 1),
                str(record["final_extracted_text"]),
                str(record["layer"]),
            )
            lookup[key] = str(record["source_type"])
        return lookup

    def _dimension_source_type(
        self,
        lookup: Dict[Tuple[float, float, str, str], str],
        x: float,
        y: float,
        clean_text: str,
        layer: str,
    ) -> Optional[str]:
        direct = lookup.get((x, y, clean_text, layer))
        if direct is not None:
            return direct

        for (ax, ay, text, lyr), source_type in lookup.items():
            if text != clean_text:
                continue
            if layer and lyr != layer:
                continue
            if math.hypot(x - ax, y - ay) <= _MATCH_TOLERANCE_MM:
                return source_type

        for (ax, ay, text, _), source_type in lookup.items():
            if text == clean_text and math.hypot(x - ax, y - ay) <= _MATCH_TOLERANCE_MM:
                return source_type

        return None

    def _build_report_text(self, summary: FilterSummary) -> str:
        lines = [
            "======================================================================",
            "Engineering Annotation Filter Report (Phase D.1.7B)",
            "======================================================================",
            "",
            f"Total input annotations: {summary['total_input_annotations']}",
            f"Engineering annotations retained: {summary['engineering_annotations']}",
            f"Geometry dimensions retained: {summary['geometry_dimensions']}",
            f"AutoCAD measurements rejected: {summary['rejected_measurements']}",
            "",
            "Engineering counts by type:",
        ]
        for type_name, count in summary["count_by_type"].items():
            lines.append(f"  {type_name}: {count}")
        lines.extend(
            [
                "",
                "Recommendation: Use engineering_annotations.json as the sole",
                "input to Phase D.2. Use geometry_dimension_annotations.json only",
                "for geometry QA. Rejected measurements are excluded from parsing.",
                "",
                "======================================================================",
            ]
        )
        return "\n".join(lines) + "\n"
