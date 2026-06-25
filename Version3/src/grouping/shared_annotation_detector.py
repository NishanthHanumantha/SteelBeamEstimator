"""Phase D.3 — detect single vs group-owned engineering annotations."""

import hashlib
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger

from src.grouping.beam_group_types import BeamGroup, OwnershipMode, SharedAnnotation
from src.utils.bbox_utils import (
    expand_bbox,
    point_in_bbox,
)

ANNOTATION_CELL_MARGIN_MM = 2500.0
ANNOTATION_DETAIL_MARGIN_MM = 3500.0
GROUP_HORIZONTAL_MARGIN_MM = 500.0
COORD_MATCH_TOLERANCE_MM = 5.0

_SHARED_NOTE_KEYWORDS = (
    "SIDE FACE",
    "SFR",
    "S F R",
    "FACE REINF",
    "FACE REINFORCEMENT",
    "ON BOTH FACE",
    "ON BOTH FACES",
    "TYPICAL",
    "CURTAIL",
    "DEVELOPMENT",
    "LAP SPLICE",
    "COVER",
    "HOOK",
    "STIRRUP",
    "REINF",
)


class SharedAnnotationDetector:
    """Classify engineering annotations as SINGLE or GROUP ownership."""

    def detect(
        self,
        engineering_records: List[dict[str, Any]],
        beam_groups: List[BeamGroup],
    ) -> List[SharedAnnotation]:
        flat = self._flatten_annotations(engineering_records)
        duplicate_map = self._duplicate_beam_map(flat)
        group_by_beam = self._beam_to_group_map(beam_groups)
        multi_groups = [g for g in beam_groups if g["is_multi_beam"]]

        shared: List[SharedAnnotation] = []
        for ann in flat:
            ann_id = self._annotation_id(ann)
            x = float(ann["x"])
            y = float(ann["y"])
            clean_text = str(ann.get("clean_text", ""))
            original_mark = str(ann["beam_mark"]).upper()

            geometric_beams = self._geometric_member_beams(x, y, multi_groups)
            duplicate_beams = sorted(
                duplicate_map.get(self._coord_key(clean_text, x, y), []),
                key=lambda m: m,
            )

            candidate_beams = sorted(
                set(geometric_beams) | set(duplicate_beams) | {original_mark},
                key=lambda m: m,
            )

            group_id: Optional[str] = None
            member_beams: List[str] = []
            signals: List[str] = []
            locked_group = False

            if len(duplicate_beams) >= 2:
                signals.append("duplicate_text_coordinates")
            if len(geometric_beams) >= 2:
                signals.append("geometric_span_multiple_beams")
            if self._looks_like_shared_note(clean_text):
                signals.append("shared_note_semantics")
                span_group = self._shared_note_group(x, y, multi_groups, original_mark)
                if span_group is not None:
                    group_id = span_group["beam_group_id"]
                    member_beams = sorted(span_group["members"], key=lambda m: m)
                    signals.append("shared_note_group_span")
                    locked_group = True

            if not locked_group and not self._looks_like_shared_note(clean_text):
                for group in multi_groups:
                    group_members = set(group["members"])
                    overlap = group_members & set(candidate_beams)
                    if len(overlap) >= 2:
                        group_id = group["beam_group_id"]
                        member_beams = sorted(group["members"], key=lambda m: m)
                        signals.append("multi_beam_group_overlap")
                        break

            if group_id is None and len(geometric_beams) >= 2 and not self._looks_like_shared_note(clean_text):
                for group in multi_groups:
                    if set(geometric_beams).issubset(set(group["members"])):
                        group_id = group["beam_group_id"]
                        member_beams = sorted(group["members"], key=lambda m: m)
                        signals.append("geometric_subset_of_group")
                        break

            if group_id is None:
                singleton_id = group_by_beam.get(original_mark)
                group_id = singleton_id
                member_beams = [original_mark]

            is_shared = (
                len(geometric_beams) >= 2
                or len(duplicate_beams) >= 2
                or (
                    self._looks_like_shared_note(clean_text)
                    and len(member_beams) >= 2
                    and group_id
                    and any(
                        g["beam_group_id"] == group_id and g["is_multi_beam"]
                        for g in beam_groups
                    )
                )
            )
            ownership_mode: OwnershipMode = (
                "GROUP" if is_shared and group_id and len(member_beams) >= 2 else "SINGLE"
            )
            if ownership_mode == "GROUP" and original_mark not in member_beams and not locked_group:
                ownership_mode = "SINGLE"
            if ownership_mode == "SINGLE":
                member_beams = [original_mark]
                group_id = group_by_beam.get(original_mark, group_id)

            shared.append(
                SharedAnnotation(
                    annotation_id=ann_id,
                    clean_text=clean_text,
                    x=x,
                    y=y,
                    annotation_type=str(ann.get("annotation_type", "")),
                    entity_type=str(ann.get("entity_type", "")),
                    ownership_mode=ownership_mode,
                    beam_group_id=group_id,
                    member_beams=member_beams,
                    geometric_member_beams=geometric_beams,
                    duplicate_member_beams=duplicate_beams,
                    detection_signals=signals,
                    original_beam_mark=original_mark,
                    original_sketch_id=str(ann.get("sketch_id", "")),
                    original_occurrence_id=int(ann.get("occurrence_id", 0)),
                    final_status=str(ann.get("final_status", "")),
                    engineering_source=str(ann.get("engineering_source", "")),
                )
            )

        group_count = sum(1 for s in shared if s["ownership_mode"] == "GROUP")
        logger.info(
            "Shared annotation detection: {} annotations — {} GROUP, {} SINGLE",
            len(shared),
            group_count,
            len(shared) - group_count,
        )
        return shared

    def _flatten_annotations(
        self, records: List[dict[str, Any]]
    ) -> List[dict[str, Any]]:
        flat: List[dict[str, Any]] = []
        for record in records:
            sketch_id = str(record.get("sketch_id", ""))
            beam_mark = str(record.get("beam_mark", ""))
            occurrence_id = int(record.get("occurrence_id", 0))
            for ann in record.get("annotations", []):
                entry = dict(ann)
                entry.setdefault("sketch_id", sketch_id)
                entry.setdefault("beam_mark", beam_mark)
                entry.setdefault("occurrence_id", occurrence_id)
                flat.append(entry)
        return flat

    def _duplicate_beam_map(
        self, annotations: List[dict[str, Any]]
    ) -> Dict[Tuple[str, float, float], List[str]]:
        buckets: Dict[Tuple[str, float, float], List[str]] = {}
        for ann in annotations:
            key = self._coord_key(str(ann.get("clean_text", "")), float(ann["x"]), float(ann["y"]))
            mark = str(ann["beam_mark"]).upper()
            buckets.setdefault(key, [])
            if mark not in buckets[key]:
                buckets[key].append(mark)
        return buckets

    def _coord_key(self, clean_text: str, x: float, y: float) -> Tuple[str, float, float]:
        normalized = re.sub(r"\s+", " ", clean_text.upper().strip())
        return (normalized, round(x, 1), round(y, 1))

    def _beam_to_group_map(self, beam_groups: List[BeamGroup]) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for group in beam_groups:
            for mark in group["members"]:
                mapping[mark] = group["beam_group_id"]
        return mapping

    def _geometric_member_beams(
        self, x: float, y: float, multi_groups: List[BeamGroup]
    ) -> List[str]:
        hits: Set[str] = set()
        for group in multi_groups:
            cell_hits = [
                m["beam_mark"]
                for m in group["member_details"]
                if point_in_bbox(x, y, m["cell_bbox"], ANNOTATION_CELL_MARGIN_MM)
            ]
            if len(cell_hits) >= 2:
                hits.update(cell_hits)
                continue

            horizontal_hits: List[str] = []
            for member in group["member_details"]:
                cell = expand_bbox(member["cell_bbox"], ANNOTATION_CELL_MARGIN_MM)
                if cell["xmin"] <= x <= cell["xmax"]:
                    horizontal_hits.append(member["beam_mark"])
            if len(horizontal_hits) >= 2:
                hits.update(horizontal_hits)
                continue

            detail_expanded = expand_bbox(group["detail_band"], ANNOTATION_DETAIL_MARGIN_MM)
            if point_in_bbox(x, y, detail_expanded) and len(horizontal_hits) == 0:
                horizontal_hits = [
                    member["beam_mark"]
                    for member in group["member_details"]
                    if expand_bbox(member["cell_bbox"], ANNOTATION_CELL_MARGIN_MM)["xmin"]
                    <= x
                    <= expand_bbox(member["cell_bbox"], ANNOTATION_CELL_MARGIN_MM)["xmax"]
                ]
            if len(horizontal_hits) >= 2 and point_in_bbox(x, y, detail_expanded):
                hits.update(horizontal_hits)

        return sorted(hits)

    def _shared_note_group(
        self,
        x: float,
        y: float,
        multi_groups: List[BeamGroup],
        original_mark: str,
    ) -> Optional[BeamGroup]:
        candidates: List[BeamGroup] = []
        for group in multi_groups:
            row_band = expand_bbox(group["bounding_box"], ANNOTATION_CELL_MARGIN_MM)
            detail_reach = expand_bbox(group["detail_band"], ANNOTATION_DETAIL_MARGIN_MM)
            horizontal = expand_bbox(group["bounding_box"], GROUP_HORIZONTAL_MARGIN_MM)
            if not (point_in_bbox(x, y, row_band) or point_in_bbox(x, y, detail_reach)):
                continue
            if horizontal["xmin"] <= x <= horizontal["xmax"]:
                candidates.append(group)

        if not candidates:
            return None

        def detail_hit_count(group: BeamGroup) -> int:
            count = 0
            for member in group["member_details"]:
                band = expand_bbox(member["detail_band"], ANNOTATION_CELL_MARGIN_MM)
                if band["xmin"] <= x <= band["xmax"]:
                    count += 1
            return count

        candidates = [group for group in candidates if detail_hit_count(group) >= 2]
        if not candidates:
            return None

        owned_candidates = [group for group in candidates if original_mark in group["members"]]
        best_hits = max(detail_hit_count(group) for group in candidates)
        top = [group for group in candidates if detail_hit_count(group) == best_hits]

        if owned_candidates:
            owned_top = [group for group in top if group in owned_candidates]
            if owned_top:
                return self._pick_closest_group(x, y, owned_top)
            owned_best = max(detail_hit_count(group) for group in owned_candidates)
            if best_hits > owned_best:
                return self._pick_closest_group(x, y, top)
            return self._pick_closest_group(x, y, owned_candidates)

        return None

    def _pick_closest_group(
        self, x: float, y: float, groups: List[BeamGroup]
    ) -> BeamGroup:
        if len(groups) == 1:
            return groups[0]
        return min(
            groups,
            key=lambda group: math.hypot(
                x - group["centroid"]["x"],
                y - group["centroid"]["y"],
            ),
        )

    def _looks_like_shared_note(self, clean_text: str) -> bool:
        upper = clean_text.upper()
        return any(keyword in upper for keyword in _SHARED_NOTE_KEYWORDS)

    def _annotation_id(self, ann: dict[str, Any]) -> str:
        payload = (
            f"{ann.get('clean_text')}|{ann.get('x')}|{ann.get('y')}|"
            f"{ann.get('sketch_id')}|{ann.get('beam_mark')}"
        )
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
