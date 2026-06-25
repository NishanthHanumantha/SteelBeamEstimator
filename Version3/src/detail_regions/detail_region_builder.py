"""Phase D.3.2 — enrich detail regions with annotations and titles."""

import math
from typing import Any, Dict, List, Tuple

from src.utils.bbox_utils import expand_bbox, point_in_bbox, union_bbox

ANNOTATION_MARGIN_MM = 800.0


class DetailRegionBuilder:
    """Attach engineering annotations and expand region envelopes."""

    def enrich(
        self,
        regions: List[dict[str, Any]],
        engineering_records: List[dict[str, Any]],
        header_occurrences: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        flat_annotations = self._flatten_annotations(engineering_records)
        headers = self._index_headers(header_occurrences)

        enriched: List[dict[str, Any]] = []
        for region in regions:
            envelope = expand_bbox(region["bbox"], ANNOTATION_MARGIN_MM)
            member_anns = [
                ann
                for ann in flat_annotations
                if point_in_bbox(
                    float(ann["x"]),
                    float(ann["y"]),
                    envelope,
                )
            ]
            if member_anns:
                envelope = union_bbox(
                    [envelope]
                    + [
                        {
                            "xmin": float(a["x"]) - 50,
                            "ymin": float(a["y"]) - 50,
                            "xmax": float(a["x"]) + 50,
                            "ymax": float(a["y"]) + 50,
                        }
                        for a in member_anns
                    ]
                )

            region_copy = dict(region)
            region_copy["bbox"] = envelope
            region_copy["member_annotations"] = [
                {
                    "clean_text": ann.get("clean_text", ""),
                    "x": ann["x"],
                    "y": ann["y"],
                    "annotation_type": ann.get("annotation_type", ""),
                    "beam_mark": ann.get("beam_mark", ""),
                    "sketch_id": ann.get("sketch_id", ""),
                }
                for ann in member_anns
            ]
            region_copy["assigned_titles"] = list(region["beam_titles"])
            region_copy["header_positions"] = [
                {
                    "beam_mark": mark,
                    "x": headers[mark][0],
                    "y": headers[mark][1],
                }
                for mark in region["beam_titles"]
                if mark in headers
            ]
            enriched.append(region_copy)
        return enriched

    def _flatten_annotations(
        self, records: List[dict[str, Any]]
    ) -> List[dict[str, Any]]:
        flat: List[dict[str, Any]] = []
        for record in records:
            for ann in record.get("annotations", []):
                entry = dict(ann)
                entry.setdefault("beam_mark", record.get("beam_mark", ""))
                entry.setdefault("sketch_id", record.get("sketch_id", ""))
                flat.append(entry)
        return flat

    def _index_headers(
        self, occurrences: List[dict[str, Any]]
    ) -> Dict[str, Tuple[float, float]]:
        index: Dict[str, Tuple[float, float]] = {}
        for occ in occurrences:
            mark = str(occ["beam_mark"]).upper()
            if mark not in index:
                index[mark] = (float(occ["x"]), float(occ["y"]))
        return index
