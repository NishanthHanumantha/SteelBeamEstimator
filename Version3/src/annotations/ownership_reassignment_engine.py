"""Phase D.1.4 — reassign annotations flagged as REASSIGN_CANDIDATE."""

import copy
import math
from collections import defaultdict
from typing import Any, Dict, List, Tuple, TypedDict

from loguru import logger

from src.framing.beam_geometry import beam_mark_sort_key


class PreviousOwner(TypedDict):
    beam_mark: str
    occurrence_id: int
    sketch_id: str


class ReassignedAnnotation(TypedDict, total=False):
    text: str
    x: float
    y: float
    ownership_source: str
    previous_owner: PreviousOwner


class OccurrenceAnnotationRecord(TypedDict):
    beam_mark: str
    occurrence_id: int
    annotations: List[ReassignedAnnotation]


class ReassignmentLogEntry(TypedDict):
    annotation: str
    x: float
    y: float
    old_owner: Dict[str, Any]
    new_owner: Dict[str, Any]
    reason: str
    current_distance_mm: float
    neighbor_distance_mm: float


class ReassignmentSummary(TypedDict):
    total_annotations: int
    reassigned: int
    unchanged: int
    consolidated: int
    affected_beams: List[str]


class ReassignmentValidation(TypedDict):
    status: str
    total_annotations: int
    post_reassignment_total: int
    expected_total: int
    reassigned: int
    expected_reassigned: int
    consolidated: int
    candidates_processed: int
    expected_candidates: int
    duplicates: int
    checks: Dict[str, bool]


class OwnershipReassignmentEngine:
    """Move REASSIGN_CANDIDATE annotations to nearest ownership regions."""

    def reassign(
        self,
        annotations_raw: List[dict[str, Any]],
        leakage_report: List[dict[str, Any]],
        ownership: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
    ) -> Tuple[
        List[OccurrenceAnnotationRecord],
        List[ReassignmentLogEntry],
        ReassignmentSummary,
        ReassignmentValidation,
        List[dict[str, Any]],
    ]:
        sketch_lookup = {str(sketch["sketch_id"]): sketch for sketch in sketches}
        sketches_by_occurrence = self._sketches_by_occurrence(ownership)

        corrected_sketches = copy.deepcopy(annotations_raw)
        log_entries: List[ReassignmentLogEntry] = []
        consolidated_count = 0
        candidates = self._eligible_candidates(leakage_report)

        for candidate in candidates:
            entry, consolidated = self._apply_reassignment(
                candidate,
                corrected_sketches,
                sketches_by_occurrence,
                sketch_lookup,
            )
            if entry is not None:
                log_entries.append(entry)
                if consolidated:
                    consolidated_count += 1

        occurrence_records = self._build_occurrence_records(corrected_sketches, log_entries)
        input_total = self._count_annotations(annotations_raw)
        summary = self._build_summary(
            input_total, log_entries, consolidated_count
        )
        validation = self._validate(
            corrected_sketches,
            candidates,
            log_entries,
            consolidated_count,
            expected_total=input_total,
        )

        logger.info(
            "Reassignment: {} total, {} reassigned, {} unchanged, status={}",
            summary["total_annotations"],
            summary["reassigned"],
            summary["unchanged"],
            validation["status"],
        )
        return occurrence_records, log_entries, summary, validation, corrected_sketches

    def _eligible_candidates(
        self, leakage_report: List[dict[str, Any]]
    ) -> List[dict[str, Any]]:
        candidates: List[dict[str, Any]] = []
        for record in leakage_report:
            if str(record.get("classification")) != "REASSIGN_CANDIDATE":
                continue
            current_dist = float(record["distance_to_current_region_mm"])
            neighbor_dist = float(record["distance_to_neighbor_region_mm"])
            nearest = record.get("nearest_region")
            if nearest is None or neighbor_dist >= current_dist:
                continue
            candidates.append(record)
        return candidates

    def _apply_reassignment(
        self,
        candidate: dict[str, Any],
        corrected_sketches: List[dict[str, Any]],
        sketches_by_occurrence: Dict[Tuple[str, int], List[str]],
        sketch_lookup: Dict[str, dict[str, Any]],
    ) -> Tuple[ReassignmentLogEntry | None, bool]:
        source_mark = str(candidate["beam_mark"])
        source_occ = int(candidate["occurrence_id"])
        source_sketch = str(candidate["sketch_id"])
        text = str(candidate["annotation"])
        x = float(candidate["x"])
        y = float(candidate["y"])

        nearest = candidate["nearest_region"]
        target_mark = str(nearest["beam_mark"])
        target_occ = int(nearest["occurrence_id"])

        removed = self._remove_from_sketch(
            corrected_sketches,
            source_mark,
            source_occ,
            source_sketch,
            text,
            x,
            y,
        )
        if removed is None:
            logger.warning(
                "Reassignment source not found: {} {} ({}, {})",
                source_sketch,
                text,
                x,
                y,
            )
            return None, False

        target_sketches = sketches_by_occurrence.get((target_mark, target_occ), [])
        if not target_sketches:
            logger.warning(
                "No owned sketches for target {} occurrence {}",
                target_mark,
                target_occ,
            )
            self._restore_to_sketch(
                corrected_sketches,
                source_mark,
                source_occ,
                source_sketch,
                text,
                x,
                y,
            )
            return None, False

        already_at_target = self._occurrence_has_annotation(
            corrected_sketches, target_mark, target_occ, text, x, y
        )
        if not already_at_target:
            target_sketch = self._nearest_sketch_id(
                target_sketches, sketch_lookup, x, y
            )
            self._add_to_sketch(
                corrected_sketches,
                target_mark,
                target_occ,
                target_sketch,
                text,
                x,
                y,
            )

        entry = ReassignmentLogEntry(
            annotation=text,
            x=round(x, 1),
            y=round(y, 1),
            old_owner={
                "beam_mark": source_mark,
                "occurrence_id": source_occ,
                "sketch_id": source_sketch,
            },
            new_owner={
                "beam_mark": target_mark,
                "occurrence_id": target_occ,
            },
            reason="REASSIGN_CANDIDATE",
            current_distance_mm=float(candidate["distance_to_current_region_mm"]),
            neighbor_distance_mm=float(candidate["distance_to_neighbor_region_mm"]),
        )
        return entry, already_at_target

    def _restore_to_sketch(
        self,
        records: List[dict[str, Any]],
        beam_mark: str,
        occurrence_id: int,
        sketch_id: str,
        text: str,
        x: float,
        y: float,
    ) -> None:
        self._add_to_sketch(
            records, beam_mark, occurrence_id, sketch_id, text, x, y
        )

    def _remove_from_sketch(
        self,
        records: List[dict[str, Any]],
        beam_mark: str,
        occurrence_id: int,
        sketch_id: str,
        text: str,
        x: float,
        y: float,
    ) -> dict[str, Any] | None:
        for record in records:
            if (
                str(record["beam_mark"]) == beam_mark
                and int(record["occurrence_id"]) == occurrence_id
                and str(record["sketch_id"]) == sketch_id
            ):
                texts = record.get("texts", [])
                for index, item in enumerate(texts):
                    if self._text_matches(item, text, x, y):
                        removed = texts.pop(index)
                        record["annotation_count"] = len(texts)
                        return removed
        return None

    def _add_to_sketch(
        self,
        records: List[dict[str, Any]],
        beam_mark: str,
        occurrence_id: int,
        sketch_id: str,
        text: str,
        x: float,
        y: float,
    ) -> None:
        for record in records:
            if (
                str(record["beam_mark"]) == beam_mark
                and int(record["occurrence_id"]) == occurrence_id
                and str(record["sketch_id"]) == sketch_id
            ):
                if self._sketch_has_text(record, text, x, y):
                    return
                record.setdefault("texts", []).append(
                    {"text": text, "x": round(x, 1), "y": round(y, 1)}
                )
                record["annotation_count"] = len(record["texts"])
                return

        records.append(
            {
                "beam_mark": beam_mark,
                "occurrence_id": occurrence_id,
                "sketch_id": sketch_id,
                "annotation_count": 1,
                "texts": [{"text": text, "x": round(x, 1), "y": round(y, 1)}],
            }
        )

    @staticmethod
    def _sketch_has_text(
        record: dict[str, Any], text: str, x: float, y: float
    ) -> bool:
        for item in record.get("texts", []):
            if OwnershipReassignmentEngine._text_matches(item, text, x, y):
                return True
        return False

    def _occurrence_has_annotation(
        self,
        records: List[dict[str, Any]],
        beam_mark: str,
        occurrence_id: int,
        text: str,
        x: float,
        y: float,
    ) -> bool:
        for record in records:
            if (
                str(record["beam_mark"]) == beam_mark
                and int(record["occurrence_id"]) == occurrence_id
            ):
                for item in record.get("texts", []):
                    if self._text_matches(item, text, x, y):
                        return True
        return False

    def _build_occurrence_records(
        self,
        corrected_sketches: List[dict[str, Any]],
        log_entries: List[ReassignmentLogEntry],
    ) -> List[OccurrenceAnnotationRecord]:
        reassigned_at_target: Dict[Tuple[str, int, str, float, float], PreviousOwner] = {}
        for entry in log_entries:
            new_mark = str(entry["new_owner"]["beam_mark"])
            new_occ = int(entry["new_owner"]["occurrence_id"])
            key = (
                new_mark,
                new_occ,
                entry["annotation"],
                round(entry["x"], 1),
                round(entry["y"], 1),
            )
            reassigned_at_target[key] = PreviousOwner(
                beam_mark=str(entry["old_owner"]["beam_mark"]),
                occurrence_id=int(entry["old_owner"]["occurrence_id"]),
                sketch_id=str(entry["old_owner"]["sketch_id"]),
            )

        grouped: Dict[Tuple[str, int], List[ReassignedAnnotation]] = defaultdict(list)
        seen_per_occurrence: set[Tuple[str, int, str, float, float]] = set()

        for record in corrected_sketches:
            beam_mark = str(record["beam_mark"])
            occurrence_id = int(record["occurrence_id"])
            for item in record.get("texts", []):
                text = str(item["text"])
                x = float(item["x"])
                y = float(item["y"])
                dedupe_key = (beam_mark, occurrence_id, text, x, y)
                if dedupe_key in seen_per_occurrence:
                    continue
                seen_per_occurrence.add(dedupe_key)

                target_key = (beam_mark, occurrence_id, text, x, y)
                if target_key in reassigned_at_target:
                    annotation: ReassignedAnnotation = {
                        "text": text,
                        "x": round(x, 1),
                        "y": round(y, 1),
                        "ownership_source": "REASSIGNED",
                        "previous_owner": reassigned_at_target[target_key],
                    }
                else:
                    annotation = {
                        "text": text,
                        "x": round(x, 1),
                        "y": round(y, 1),
                    }

                grouped[(beam_mark, occurrence_id)].append(annotation)

        occurrence_records: List[OccurrenceAnnotationRecord] = []
        for key in sorted(
            grouped.keys(),
            key=lambda item: (beam_mark_sort_key(item[0]), item[1]),
        ):
            mark, occurrence_id = key
            annotations = grouped[key]
            annotations.sort(key=lambda item: (-item["y"], item["x"], item["text"]))
            occurrence_records.append(
                OccurrenceAnnotationRecord(
                    beam_mark=mark,
                    occurrence_id=occurrence_id,
                    annotations=annotations,
                )
            )
        return occurrence_records

    @staticmethod
    def _sketches_by_occurrence(
        ownership: List[dict[str, Any]],
    ) -> Dict[Tuple[str, int], List[str]]:
        mapping: Dict[Tuple[str, int], List[str]] = defaultdict(list)
        for record in ownership:
            mark = str(record["beam_mark"])
            occurrence_id = int(record["occurrence_id"])
            key = (mark, occurrence_id)
            for item in record.get("owned_sketches", []):
                sketch_id = (
                    str(item["sketch_id"]) if isinstance(item, dict) else str(item)
                )
                mapping[key].append(sketch_id)
        return mapping

    @staticmethod
    def _nearest_sketch_id(
        sketch_ids: List[str],
        sketch_lookup: Dict[str, dict[str, Any]],
        x: float,
        y: float,
    ) -> str:
        best_id = sketch_ids[0]
        best_dist = float("inf")
        for sketch_id in sketch_ids:
            sketch = sketch_lookup.get(sketch_id)
            if sketch is None:
                continue
            bbox = sketch["bbox"]
            cx = (float(bbox["xmin"]) + float(bbox["xmax"])) / 2.0
            cy = (float(bbox["ymin"]) + float(bbox["ymax"])) / 2.0
            dist = math.hypot(cx - x, cy - y)
            if dist < best_dist:
                best_dist = dist
                best_id = sketch_id
        return best_id

    @staticmethod
    def _text_matches(item: dict[str, Any], text: str, x: float, y: float) -> bool:
        return (
            str(item["text"]) == text
            and float(item["x"]) == round(x, 1)
            and float(item["y"]) == round(y, 1)
        )

    def _build_summary(
        self,
        input_total: int,
        log_entries: List[ReassignmentLogEntry],
        consolidated_count: int,
    ) -> ReassignmentSummary:
        reassigned = len(log_entries)
        affected: set[str] = set()
        for entry in log_entries:
            affected.add(str(entry["old_owner"]["beam_mark"]))
            affected.add(str(entry["new_owner"]["beam_mark"]))

        return ReassignmentSummary(
            total_annotations=input_total,
            reassigned=reassigned,
            unchanged=input_total - reassigned,
            consolidated=consolidated_count,
            affected_beams=sorted(affected, key=beam_mark_sort_key),
        )

    def _validate(
        self,
        corrected_sketches: List[dict[str, Any]],
        candidates: List[dict[str, Any]],
        log_entries: List[ReassignmentLogEntry],
        consolidated_count: int,
        expected_total: int,
    ) -> ReassignmentValidation:
        post_total = self._count_annotations(corrected_sketches)
        reassigned = len(log_entries)
        expected_candidates = len(candidates)
        duplicates = self._count_duplicates(corrected_sketches)

        checks = {
            "all_candidates_processed": reassigned == expected_candidates,
            "no_duplicates": duplicates == 0,
            "no_missing": post_total + consolidated_count == expected_total,
            "count_matches_expected": post_total + consolidated_count == expected_total,
            "reassigned_matches_candidates": reassigned == expected_candidates,
        }
        status = "PASS" if all(checks.values()) else "FAIL"

        return ReassignmentValidation(
            status=status,
            total_annotations=expected_total,
            post_reassignment_total=post_total,
            expected_total=expected_total,
            reassigned=reassigned,
            expected_reassigned=expected_candidates,
            consolidated=consolidated_count,
            candidates_processed=reassigned,
            expected_candidates=expected_candidates,
            duplicates=duplicates,
            checks=checks,
        )

    @staticmethod
    def _count_annotations(records: List[dict[str, Any]]) -> int:
        return sum(len(record.get("texts", [])) for record in records)

    @staticmethod
    def _count_duplicates(records: List[dict[str, Any]]) -> int:
        seen: set[Tuple[str, int, str, float, float]] = set()
        duplicates = 0
        for record in records:
            beam_mark = str(record["beam_mark"])
            occurrence_id = int(record["occurrence_id"])
            sketch_id = str(record["sketch_id"])
            for item in record.get("texts", []):
                key = (
                    beam_mark,
                    occurrence_id,
                    sketch_id,
                    float(item["x"]),
                    float(item["y"]),
                )
                if key in seen:
                    duplicates += 1
                seen.add(key)
        return duplicates
