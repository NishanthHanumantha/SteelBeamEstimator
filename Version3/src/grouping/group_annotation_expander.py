"""Phase D.3 — expand group-owned annotations to member beams."""

import math
from typing import Any, Dict, List, Optional

from loguru import logger

from src.framing.beam_geometry import beam_mark_sort_key
from src.grouping.beam_group_types import ExpandedAnnotation, GroupOwnershipRecord
from src.utils.bbox_utils import distance_point_to_bbox, sketches_for_beam


class GroupAnnotationExpander:
    """Expand shared annotations to per-beam records with full traceability."""

    def expand(
        self,
        ownership_records: List[GroupOwnershipRecord],
        sketches: List[dict[str, Any]],
        sketch_ownership: List[dict[str, Any]],
    ) -> List[ExpandedAnnotation]:
        sketch_owner = self._sketch_owner_map(sketch_ownership)
        expanded: List[ExpandedAnnotation] = []

        for record in ownership_records:
            if record["ownership_mode"] == "GROUP":
                for mark in sorted(record["member_beams"], key=beam_mark_sort_key):
                    sketch_id, occurrence_id = self._best_sketch_for_beam(
                        mark, float(record["x"]), float(record["y"]), sketches, sketch_owner
                    )
                    expanded.append(
                        self._expanded_entry(record, mark, sketch_id, occurrence_id, True)
                    )
            else:
                mark = record["member_beams"][0]
                sketch_id = record.get("original_sketch_id", "")
                occurrence_id = sketch_owner.get(sketch_id, (mark, 1))[1]
                expanded.append(
                    self._expanded_entry(record, mark, sketch_id, occurrence_id, False)
                )

        logger.info("Expanded {} ownership record(s) to {} beam annotations", len(ownership_records), len(expanded))
        return expanded

    def _expanded_entry(
        self,
        record: GroupOwnershipRecord,
        beam_mark: str,
        sketch_id: str,
        occurrence_id: int,
        from_group: bool,
    ) -> ExpandedAnnotation:
        return ExpandedAnnotation(
            shared_annotation_id=record["annotation_id"],
            beam_group_id=record["beam_group_id"],
            expanded_from_group=from_group,
            beam_mark=beam_mark,
            occurrence_id=occurrence_id,
            sketch_id=sketch_id,
            clean_text=record["clean_text"],
            x=record["x"],
            y=record["y"],
            annotation_type=record.get("annotation_type", ""),
            entity_type="",
            final_status="PARSER_READY",
            engineering_source="GROUP_EXPANSION",
            original_annotation_reference={
                "beam_mark": record["original_beam_mark"],
                "sketch_id": record.get("original_sketch_id", ""),
                "clean_text": record["clean_text"],
                "x": record["x"],
                "y": record["y"],
                "ownership_source": record["ownership_source"],
            },
        )

    def _sketch_owner_map(
        self, sketch_ownership: List[dict[str, Any]]
    ) -> Dict[str, tuple[str, int]]:
        mapping: Dict[str, tuple[str, int]] = {}
        for entry in sketch_ownership:
            mark = str(entry["beam_mark"]).upper()
            occ_id = int(entry["occurrence_id"])
            for owned in entry.get("owned_sketches", []):
                sketch_id = str(owned["sketch_id"])
                mapping[sketch_id] = (mark, occ_id)
        return mapping

    def _best_sketch_for_beam(
        self,
        beam_mark: str,
        x: float,
        y: float,
        sketches: List[dict[str, Any]],
        sketch_owner: Dict[str, tuple[str, int]],
    ) -> tuple[str, int]:
        candidates = sketches_for_beam(beam_mark, sketches)
        if not candidates:
            occ_ids = [
                occ for mark, occ in sketch_owner.values() if mark == beam_mark
            ]
            return f"{beam_mark}_S1", occ_ids[0] if occ_ids else 1

        best = min(
            candidates,
            key=lambda sk: distance_point_to_bbox(x, y, sk["bbox"]),
        )
        sketch_id = str(best["sketch_id"])
        owner = sketch_owner.get(sketch_id, (beam_mark, 1))
        return sketch_id, owner[1]
