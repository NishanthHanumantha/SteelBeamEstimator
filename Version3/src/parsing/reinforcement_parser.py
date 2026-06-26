"""Phase D.4 — batch engineering annotation parsing."""

from typing import Any, Dict, List, Optional

from loguru import logger

from src.parsing.engineering_annotation_parser import EngineeringAnnotationParser


class ReinforcementParser:
    """Parse all owned annotations from D.3.3 ownership master."""

    def __init__(self) -> None:
        self._parser = EngineeringAnnotationParser()

    def parse_all(
        self,
        ownership_records: List[dict[str, Any]],
        beam_groups: List[dict[str, Any]],
        sketch_index: Dict[str, dict[str, Any]],
    ) -> Dict[str, List[dict[str, Any]]]:
        group_by_region = {
            g["detail_region_id"]: g["beam_group_id"] for g in beam_groups
        }
        owned = [
            r for r in ownership_records if r.get("ownership_status") == "OWNED"
        ]
        objects: List[dict[str, Any]] = []
        longitudinal: List[dict[str, Any]] = []
        stirrups: List[dict[str, Any]] = []
        anchorage_list: List[dict[str, Any]] = []
        sfr_list: List[dict[str, Any]] = []
        failed: List[dict[str, Any]] = []

        for record in owned:
            region_id = record.get("detail_region_id")
            beam_group_id = group_by_region.get(region_id)
            sketch_id = str(record.get("resolved_sketch_id", ""))
            sketch = sketch_index.get(sketch_id)
            sketch_bbox = sketch["bbox"] if sketch else None

            obj = self._parser.parse_record(record, beam_group_id, sketch_bbox)
            objects.append(obj)

            eng_type = obj.get("engineering_type", "UNKNOWN")
            status = obj.get("parser_status", "FAILED")

            if status != "SUCCESS":
                failed.append(obj)
                continue

            if eng_type == "LONGITUDINAL_BAR":
                longitudinal.append(obj)
            elif eng_type == "STIRRUP":
                stirrups.append(obj)
            elif eng_type in ("ANCHORAGE", "HOOK"):
                anchorage_list.append(obj)
            elif eng_type == "SIDE_FACE_REINFORCEMENT":
                sfr_list.append(obj)

        logger.info(
            "Parsed {} owned annotation(s) — {} longitudinal, {} stirrup, "
            "{} anchorage, {} SFR, {} failed",
            len(owned),
            len(longitudinal),
            len(stirrups),
            len(anchorage_list),
            len(sfr_list),
            len(failed),
        )
        return {
            "engineering_objects": objects,
            "parsed_longitudinal_bars": longitudinal,
            "parsed_stirrups": stirrups,
            "parsed_anchorage": anchorage_list,
            "parsed_sfr": sfr_list,
            "failed": failed,
        }
