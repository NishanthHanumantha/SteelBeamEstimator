"""Phase D.1.5 — post-reassignment ownership validation (read-only)."""

import math
from collections import defaultdict
from typing import Any, Dict, List, Tuple, TypedDict

from loguru import logger

from src.annotations.annotation_ownership_auditor import AnnotationOwnershipAuditor
from src.annotations.annotation_region_validator import AnnotationRegionValidator
from src.annotations.boundary_leakage_analyzer import BoundaryLeakageAnalyzer


class PostReassignmentSummary(TypedDict):
    ownership_status: str
    region_status: str
    validation_status: str
    total_annotations: int
    high_confidence: int
    medium_confidence: int
    low_confidence: int
    suspicious: int
    inside_region: int
    near_region_edge: int
    outside_region: int
    retain: int
    review: int
    reassign_candidate: int
    improvement_vs_d13: Dict[str, int]
    recommendation: str


class PostReassignmentValidation(TypedDict):
    status: str
    ownership_integrity: bool
    no_orphan_annotations: bool
    no_duplicate_ownership: bool
    reassign_candidate_zero: bool
    checks: Dict[str, bool]


class PostReassignmentValidator:
    """Re-run D.1.1, D.1.3, and D.1.3.1 validations on reassigned annotations."""

    def validate(
        self,
        reassigned: List[dict[str, Any]],
        ownership: List[dict[str, Any]],
        occurrences: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
        beam_cells: List[dict[str, Any]],
        d13_region_summary: dict[str, Any] | None = None,
        d131_leakage_summary: dict[str, Any] | None = None,
    ) -> Tuple[
        List[dict[str, Any]],
        dict[str, Any],
        List[dict[str, Any]],
        dict[str, Any],
        List[dict[str, Any]],
        dict[str, Any],
        PostReassignmentSummary,
        PostReassignmentValidation,
        Dict[Tuple[str, int], Any],
    ]:
        sketch_records = self._to_sketch_records(reassigned, ownership, sketches)
        integrity = self._check_integrity(reassigned, sketch_records, ownership)

        auditor = AnnotationOwnershipAuditor()
        audit_records = auditor.audit(sketch_records, sketches)
        ownership_validation = auditor.build_validation(audit_records)

        region_validator = AnnotationRegionValidator()
        region_records, region_summary, regions = region_validator.validate(
            sketch_records,
            ownership,
            occurrences,
            sketches,
            beam_cells,
        )

        leakage_analyzer = BoundaryLeakageAnalyzer()
        leakage_records, leakage_summary, leakage_validation, _ = leakage_analyzer.analyze(
            region_records,
            ownership,
            occurrences,
            sketches,
            beam_cells,
        )

        d13_outside = int(d13_region_summary.get("outside_region", 5) if d13_region_summary else 5)
        d131_candidates = int(
            d131_leakage_summary.get("reassign_candidate", 5) if d131_leakage_summary else 5
        )

        summary = self._build_summary(
            ownership_validation,
            region_summary,
            leakage_summary,
            d13_outside,
            d131_candidates,
        )
        validation = self._build_validation(
            integrity,
            leakage_summary,
            summary,
        )

        logger.info(
            "Post-reassignment validation: ownership={}, region={}, status={}, recommendation={}",
            summary["ownership_status"],
            summary["region_status"],
            validation["status"],
            summary["recommendation"],
        )
        return (
            audit_records,
            ownership_validation,
            region_records,
            region_summary,
            leakage_records,
            leakage_summary,
            summary,
            validation,
            regions,
        )

    def build_report_text(
        self,
        summary: PostReassignmentSummary,
        audit_records: List[dict[str, Any]],
        region_records: List[dict[str, Any]],
        leakage_records: List[dict[str, Any]],
    ) -> str:
        outside_records = [
            r for r in region_records if r["classification"] == "OUTSIDE_REGION"
        ]
        suspicious_records = [
            r for r in audit_records if r["confidence"] == "SUSPICIOUS"
        ]
        candidate_records = [
            r for r in leakage_records if r["classification"] == "REASSIGN_CANDIDATE"
        ]

        improvement = summary["improvement_vs_d13"]
        lines = [
            "======================================================================",
            "Post-Reassignment Validation Report (Phase D.1.5)",
            "======================================================================",
            "",
            "D.1.3 vs D.1.5 Comparison",
            "-" * 70,
            f"  OUTSIDE_REGION:     {improvement['outside_before']} -> {improvement['outside_after']}",
            f"  REASSIGN_CANDIDATE: {improvement['candidates_before']} -> {improvement['candidates_after']}",
            "",
            "Leakage Reduction",
            "-" * 70,
            f"  Outside reduced by: {improvement['outside_before'] - improvement['outside_after']}",
            f"  Candidates reduced by: {improvement['candidates_before'] - improvement['candidates_after']}",
            "",
            "Ownership Audit Summary",
            "-" * 70,
            f"  Status: {summary['ownership_status']}",
            f"  HIGH: {summary['high_confidence']}",
            f"  MEDIUM: {summary['medium_confidence']}",
            f"  LOW: {summary['low_confidence']}",
            f"  SUSPICIOUS: {summary['suspicious']}",
            "",
            "Region Validation Summary",
            "-" * 70,
            f"  Status: {summary['region_status']}",
            f"  INSIDE_REGION: {summary['inside_region']}",
            f"  NEAR_REGION_EDGE: {summary['near_region_edge']}",
            f"  OUTSIDE_REGION: {summary['outside_region']}",
            "",
            "Leakage Analysis Summary",
            "-" * 70,
            f"  RETAIN: {summary['retain']}",
            f"  REVIEW: {summary['review']}",
            f"  REASSIGN_CANDIDATE: {summary['reassign_candidate']}",
            "",
            "Remaining Suspicious Annotations",
            "-" * 70,
        ]
        if suspicious_records:
            for record in suspicious_records:
                preview = AnnotationOwnershipAuditor._summary_annotation(
                    record["annotation"]
                )
                lines.append(
                    f"  {record['beam_mark']} {record['sketch_id']} "
                    f"{preview} — {record['distance_mm']} mm"
                )
        else:
            lines.append("  (none)")

        lines.extend(["", "Remaining OUTSIDE_REGION Annotations", "-" * 70])
        if outside_records:
            for record in outside_records:
                preview = AnnotationRegionValidator._preview_text(record["annotation"])
                lines.append(
                    f"  {record['beam_mark']} {record['sketch_id']} "
                    f"{preview} — {record['distance_to_region_mm']} mm"
                )
        else:
            lines.append("  (none)")

        lines.extend(["", "Remaining REASSIGN_CANDIDATE Annotations", "-" * 70])
        if candidate_records:
            for record in candidate_records:
                preview = AnnotationRegionValidator._preview_text(record["annotation"])
                lines.append(
                    f"  {record['beam_mark']} {record['sketch_id']} "
                    f"{preview} — neighbor {record['distance_to_neighbor_region_mm']} mm"
                )
        else:
            lines.append("  (none)")

        lines.extend(
            [
                "",
                "Final Recommendation",
                "-" * 70,
                f"  {summary['recommendation']}",
                "",
                f"Overall Validation Status: {summary['validation_status']}",
                "======================================================================",
            ]
        )
        return "\n".join(lines) + "\n"

    def _to_sketch_records(
        self,
        reassigned: List[dict[str, Any]],
        ownership: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        sketch_lookup = {str(sketch["sketch_id"]): sketch for sketch in sketches}
        sketches_by_occurrence = self._sketches_by_occurrence(ownership)
        grouped: Dict[Tuple[str, int, str], List[dict[str, Any]]] = defaultdict(list)

        for occurrence_record in reassigned:
            beam_mark = str(occurrence_record["beam_mark"])
            occurrence_id = int(occurrence_record["occurrence_id"])
            sketch_ids = sketches_by_occurrence.get((beam_mark, occurrence_id), [])
            if not sketch_ids:
                logger.warning(
                    "No owned sketches for {} occurrence {} — skipping annotations",
                    beam_mark,
                    occurrence_id,
                )
                continue

            for item in occurrence_record.get("annotations", []):
                text = str(item["text"])
                x = float(item["x"])
                y = float(item["y"])
                sketch_id = self._nearest_sketch_id(
                    sketch_ids, sketch_lookup, x, y
                )
                grouped[(beam_mark, occurrence_id, sketch_id)].append(
                    {"text": text, "x": round(x, 1), "y": round(y, 1)}
                )

        records: List[dict[str, Any]] = []
        for (beam_mark, occurrence_id, sketch_id), texts in sorted(
            grouped.items(),
            key=lambda item: (item[0][0], item[0][1], item[0][2]),
        ):
            texts.sort(key=lambda t: (-t["y"], t["x"], t["text"]))
            records.append(
                {
                    "beam_mark": beam_mark,
                    "occurrence_id": occurrence_id,
                    "sketch_id": sketch_id,
                    "annotation_count": len(texts),
                    "texts": texts,
                }
            )
        return records

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

    def _check_integrity(
        self,
        reassigned: List[dict[str, Any]],
        sketch_records: List[dict[str, Any]],
        ownership: List[dict[str, Any]],
    ) -> Dict[str, Any]:
        owned_keys = {
            (str(r["beam_mark"]), int(r["occurrence_id"])) for r in ownership
        }
        total = sum(
            len(occ.get("annotations", [])) for occ in reassigned
        )
        orphans = 0
        for occ in reassigned:
            key = (str(occ["beam_mark"]), int(occ["occurrence_id"]))
            if key not in owned_keys:
                orphans += len(occ.get("annotations", []))

        sketch_duplicates = self._count_sketch_duplicates(sketch_records)
        occurrence_duplicates = self._count_occurrence_duplicates(reassigned)

        return {
            "total_annotations": total,
            "orphan_count": orphans,
            "sketch_duplicates": sketch_duplicates,
            "occurrence_duplicates": occurrence_duplicates,
            "no_orphans": orphans == 0,
            "no_duplicates": sketch_duplicates == 0 and occurrence_duplicates == 0,
        }

    @staticmethod
    def _count_sketch_duplicates(sketch_records: List[dict[str, Any]]) -> int:
        seen: set[Tuple[str, int, str, float, float]] = set()
        duplicates = 0
        for record in sketch_records:
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

    @staticmethod
    def _count_occurrence_duplicates(reassigned: List[dict[str, Any]]) -> int:
        seen: set[Tuple[str, int, str, float, float]] = set()
        duplicates = 0
        for occ in reassigned:
            beam_mark = str(occ["beam_mark"])
            occurrence_id = int(occ["occurrence_id"])
            for item in occ.get("annotations", []):
                key = (
                    beam_mark,
                    occurrence_id,
                    str(item["text"]),
                    float(item["x"]),
                    float(item["y"]),
                )
                if key in seen:
                    duplicates += 1
                seen.add(key)
        return duplicates

    def _build_summary(
        self,
        ownership_validation: dict[str, Any],
        region_summary: dict[str, Any],
        leakage_summary: dict[str, Any],
        d13_outside: int,
        d131_candidates: int,
    ) -> PostReassignmentSummary:
        outside_after = int(region_summary["outside_region"])
        candidates_after = int(leakage_summary["reassign_candidate"])

        ownership_status = str(ownership_validation["status"])
        region_status = str(region_summary["status"])

        targets_met = (
            candidates_after == 0
            and outside_after <= 1
            and ownership_status == "PASS"
            and region_status == "PASS"
        )
        recommendation = "READY_FOR_D2" if targets_met else "REQUIRES_FURTHER_CLEANUP"

        validation_status = self._overall_status(
            ownership_status,
            region_status,
            candidates_after,
            outside_after,
        )

        return PostReassignmentSummary(
            ownership_status=ownership_status,
            region_status=region_status,
            validation_status=validation_status,
            total_annotations=int(ownership_validation["total_annotations"]),
            high_confidence=int(ownership_validation["high_confidence"]),
            medium_confidence=int(ownership_validation["medium_confidence"]),
            low_confidence=int(ownership_validation["low_confidence"]),
            suspicious=int(ownership_validation["suspicious"]),
            inside_region=int(region_summary["inside_region"]),
            near_region_edge=int(region_summary["near_region_edge"]),
            outside_region=outside_after,
            retain=int(leakage_summary["retain"]),
            review=int(leakage_summary["review"]),
            reassign_candidate=candidates_after,
            improvement_vs_d13={
                "outside_before": d13_outside,
                "outside_after": outside_after,
                "candidates_before": d131_candidates,
                "candidates_after": candidates_after,
            },
            recommendation=recommendation,
        )

    @staticmethod
    def _overall_status(
        ownership_status: str,
        region_status: str,
        reassign_candidate: int,
        outside_region: int,
    ) -> str:
        if reassign_candidate > 0:
            return "FAIL"
        if outside_region > 0:
            return "PASS_WITH_WARNINGS"
        if ownership_status == "FAIL" or region_status == "FAIL":
            return "FAIL"
        if ownership_status == "PASS_WITH_WARNINGS":
            return "PASS_WITH_WARNINGS"
        return "PASS"

    def _build_validation(
        self,
        integrity: Dict[str, Any],
        leakage_summary: dict[str, Any],
        summary: PostReassignmentSummary,
    ) -> PostReassignmentValidation:
        reassign_zero = int(leakage_summary["reassign_candidate"]) == 0
        integrity_ok = integrity["no_orphans"] and integrity["no_duplicates"]

        checks = {
            "ownership_integrity": integrity_ok,
            "no_orphan_annotations": integrity["no_orphans"],
            "no_duplicate_ownership": integrity["no_duplicates"],
            "reassign_candidate_zero": reassign_zero,
        }

        if not integrity_ok or not reassign_zero:
            status = "FAIL"
        elif summary["outside_region"] > 0:
            status = "PASS_WITH_WARNINGS"
        else:
            status = "PASS"

        return PostReassignmentValidation(
            status=status,
            ownership_integrity=integrity_ok,
            no_orphan_annotations=integrity["no_orphans"],
            no_duplicate_ownership=integrity["no_duplicates"],
            reassign_candidate_zero=reassign_zero,
            checks=checks,
        )
