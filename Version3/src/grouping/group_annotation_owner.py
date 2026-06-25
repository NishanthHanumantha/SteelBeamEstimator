"""Phase D.3 — assign annotations to beam groups."""

from typing import Any, Dict, List

from src.grouping.beam_group_types import GroupOwnershipRecord, SharedAnnotation


class GroupAnnotationOwner:
    """Replace nearest-sketch ownership with beam-group ownership."""

    def assign(self, shared_annotations: List[SharedAnnotation]) -> List[GroupOwnershipRecord]:
        records: List[GroupOwnershipRecord] = []
        for ann in shared_annotations:
            mode = ann["ownership_mode"]
            source = self._ownership_source(ann)
            records.append(
                GroupOwnershipRecord(
                    annotation_id=ann["annotation_id"],
                    ownership_mode=mode,
                    beam_group_id=str(ann.get("beam_group_id", "")),
                    member_beams=list(ann.get("member_beams", [])),
                    ownership_source=source,
                    clean_text=ann["clean_text"],
                    x=ann["x"],
                    y=ann["y"],
                    annotation_type=ann.get("annotation_type", ""),
                    original_beam_mark=ann["original_beam_mark"],
                    original_sketch_id=ann["original_sketch_id"],
                )
            )
        return records

    def _ownership_source(self, ann: SharedAnnotation) -> str:
        signals = ann.get("detection_signals", [])
        if "duplicate_text_coordinates" in signals:
            return "DUPLICATE_COORDINATES"
        if "geometric_span_multiple_beams" in signals:
            return "GEOMETRIC_SPAN"
        if "multi_beam_group_overlap" in signals:
            return "BEAM_GROUP_OVERLAP"
        if ann["ownership_mode"] == "GROUP":
            return "BEAM_GROUP"
        return "SINGLE_BEAM"
