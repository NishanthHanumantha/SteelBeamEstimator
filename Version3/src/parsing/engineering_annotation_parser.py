"""Phase D.4 — parse owned annotations into normalized engineering objects."""

import hashlib
from typing import Any, Dict, List, Optional

from loguru import logger

from src.parsing.anchorage_parser import parse_anchorage_text
from src.parsing.annotation_parsers import ParseError
from src.parsing.bar_parser import parse_bar_text
from src.parsing.sfr_parser import parse_sfr_text
from src.parsing.stirrup_parser import parse_stirrup_text

_TYPE_MAP = {
    "BAR": "BAR",
    "STIRRUP": "STIRRUP",
    "ANCHORAGE": "ANCHORAGE",
    "SIDE_FACE_REINF": "SIDE_FACE_REINF",
    "SIDE_FACE_REINFORCEMENT": "SIDE_FACE_REINF",
    "DIMENSION": "DIMENSION_ENGINEERING",
}


class EngineeringAnnotationParser:
    """Convert a single owned annotation record into an EngineeringObject."""

    def parse_record(
        self,
        record: dict[str, Any],
        beam_group_id: Optional[str],
        sketch_bbox: Optional[dict[str, float]],
    ) -> dict[str, Any]:
        ann_id = str(record["annotation_id"])
        clean_text = str(record.get("clean_text", "")).strip()
        ann_type = str(record.get("annotation_type", "")).upper()
        mapped = _TYPE_MAP.get(ann_type, ann_type)

        base = self._base_object(record, beam_group_id, sketch_bbox)
        try:
            if mapped == "BAR":
                fields = parse_bar_text(clean_text)
            elif mapped == "STIRRUP":
                fields = parse_stirrup_text(clean_text)
            elif mapped == "ANCHORAGE":
                fields = parse_anchorage_text(clean_text)
            elif mapped in ("SIDE_FACE_REINF", "SIDE_FACE_REINFORCEMENT"):
                fields = parse_sfr_text(clean_text)
            elif mapped == "DIMENSION_ENGINEERING":
                fields = {
                    "engineering_type": "DIMENSION_ENGINEERING",
                    "dimension_text": clean_text,
                }
            else:
                fields = {
                    "engineering_type": "UNKNOWN",
                    "parse_note": f"unsupported annotation_type: {ann_type}",
                }
                base["parser_status"] = "UNSUPPORTED"
                base.update(fields)
                base["object_id"] = self._object_id(ann_id, clean_text)
                return base

            base["parser_status"] = "SUCCESS"
            base["source_annotation_type"] = ann_type
            base.update(fields)
        except ParseError as exc:
            base["parser_status"] = "FAILED"
            base["parse_error"] = str(exc)
            base["engineering_type"] = "UNKNOWN"
            logger.debug("Parse failed {}: {}", ann_id, exc)

        base["object_id"] = self._object_id(ann_id, clean_text)
        return base

    def _base_object(
        self,
        record: dict[str, Any],
        beam_group_id: Optional[str],
        sketch_bbox: Optional[dict[str, float]],
    ) -> dict[str, Any]:
        leader = record.get("leader_endpoint")
        return {
            "source_annotation_id": record["annotation_id"],
            "clean_text": record.get("clean_text", ""),
            "coordinates": {
                "x": float(record["x"]),
                "y": float(record["y"]),
                "eval_x": float(record.get("eval_x", record["x"])),
                "eval_y": float(record.get("eval_y", record["y"])),
            },
            "leader_endpoint": leader,
            "detail_region_id": record.get("detail_region_id"),
            "beam_group_id": beam_group_id,
            "owner_sketch_id": record.get("resolved_sketch_id"),
            "resolved_beam_mark": record.get("resolved_beam_mark"),
            "expanded_beams": record.get("expanded_beams", []),
            "ownership_confidence": record.get("confidence_score"),
            "sketch_bbox": sketch_bbox,
            "entity_type": record.get("entity_type", ""),
            "engineering_source": record.get("engineering_source", ""),
        }

    def _object_id(self, annotation_id: str, clean_text: str) -> str:
        payload = f"{annotation_id}|{clean_text}"
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
