"""Validation for Phase C.5 sketch ownership."""

import re
from typing import Any, List, TypedDict

from src.grid.sketch_ownership_auditor import (
    EnrichedSketchOwnershipRecord,
    OwnershipAuditStats,
    OwnershipAuditSummary,
    OwnershipWarning,
    SketchOwnershipAuditor,
)
from src.grid.sketch_ownership_builder import SketchAssignment


class BeamMarkMismatch(TypedDict):
    beam_mark: str
    occurrence_id: int
    sketch_id: str
    sketch_beam_mark: str


class SketchOwnershipValidation(TypedDict):
    total_sketches: int
    assigned_sketches: int
    orphan_sketches: List[str]
    multi_owned_sketches: List[str]
    beam_mark_mismatches: List[BeamMarkMismatch]
    missing_ownership_sketches: List[str]
    duplicate_ownership_sketches: List[str]
    ownership_status: str
    audit_status: str
    total_assignments: int
    high_confidence: int
    medium_confidence: int
    low_confidence: int
    avg_assignment_distance_mm: float
    max_assignment_distance_mm: float
    warnings: List[OwnershipWarning]
    distance_distribution: dict[str, int]
    summary: OwnershipAuditSummary


class SketchOwnershipValidator:
    """Validate sketch-to-header-occurrence ownership assignments."""

    def __init__(self) -> None:
        self._auditor = SketchOwnershipAuditor()

    def validate(
        self,
        sketches: List[dict[str, Any]],
        assignments: List[SketchAssignment],
        enriched_ownership: List[EnrichedSketchOwnershipRecord],
        audit_stats: OwnershipAuditStats,
        warnings: List[OwnershipWarning],
        audits: List[Any],
    ) -> SketchOwnershipValidation:
        sketch_lookup = {str(sketch["sketch_id"]): sketch for sketch in sketches}
        all_sketch_ids = sorted(str(sketch["sketch_id"]) for sketch in sketches)
        assigned_ids = [assignment["sketch_id"] for assignment in assignments]

        owner_counts: dict[str, int] = {}
        for sketch_id in assigned_ids:
            owner_counts[sketch_id] = owner_counts.get(sketch_id, 0) + 1

        orphan_sketches = sorted(
            sketch_id for sketch_id in all_sketch_ids if sketch_id not in assigned_ids
        )
        multi_owned_sketches = sorted(
            sketch_id for sketch_id, count in owner_counts.items() if count > 1
        )

        beam_mark_mismatches = self._find_beam_mark_mismatches(
            assignments, sketch_lookup
        )

        ownership_sketch_ids = self._owned_sketch_ids(enriched_ownership)
        missing_ownership_sketches = sorted(
            sketch_id for sketch_id in all_sketch_ids if sketch_id not in ownership_sketch_ids
        )
        duplicate_ownership_sketches = sorted(
            sketch_id
            for sketch_id, count in self._ownership_counts(enriched_ownership).items()
            if count > 1
        )

        ownership_errors = (
            orphan_sketches
            or multi_owned_sketches
            or beam_mark_mismatches
            or missing_ownership_sketches
            or duplicate_ownership_sketches
            or len(assigned_ids) != len(all_sketch_ids)
        )
        ownership_status = "FAIL" if ownership_errors else "PASS"
        audit_status = "PASS_WITH_WARNINGS" if warnings else "PASS"

        summary = self._auditor.build_summary(
            ownership_status=ownership_status,
            audit_status=audit_status,
            stats=audit_stats,
            warnings=warnings,
            orphan_count=len(orphan_sketches),
            multi_owned_count=len(multi_owned_sketches),
            beam_mark_mismatch_count=len(beam_mark_mismatches),
        )

        return SketchOwnershipValidation(
            total_sketches=len(all_sketch_ids),
            assigned_sketches=len(assigned_ids),
            orphan_sketches=orphan_sketches,
            multi_owned_sketches=multi_owned_sketches,
            beam_mark_mismatches=beam_mark_mismatches,
            missing_ownership_sketches=missing_ownership_sketches,
            duplicate_ownership_sketches=duplicate_ownership_sketches,
            ownership_status=ownership_status,
            audit_status=audit_status,
            total_assignments=audit_stats["total_assignments"],
            high_confidence=audit_stats["high_confidence"],
            medium_confidence=audit_stats["medium_confidence"],
            low_confidence=audit_stats["low_confidence"],
            avg_assignment_distance_mm=audit_stats["avg_assignment_distance_mm"],
            max_assignment_distance_mm=audit_stats["max_assignment_distance_mm"],
            warnings=warnings,
            distance_distribution=self._auditor.compute_distance_distribution(audits),
            summary=summary,
        )

    def _find_beam_mark_mismatches(
        self,
        assignments: List[SketchAssignment],
        sketch_lookup: dict[str, dict[str, Any]],
    ) -> List[BeamMarkMismatch]:
        mismatches: List[BeamMarkMismatch] = []
        for assignment in assignments:
            sketch = sketch_lookup.get(assignment["sketch_id"])
            if sketch is None:
                continue
            sketch_mark = str(sketch["beam_mark"]).upper()
            header_mark = assignment["beam_mark"].upper()
            if sketch_mark != header_mark:
                mismatches.append(
                    BeamMarkMismatch(
                        beam_mark=assignment["beam_mark"],
                        occurrence_id=assignment["occurrence_id"],
                        sketch_id=assignment["sketch_id"],
                        sketch_beam_mark=sketch_mark,
                    )
                )
            elif not self._sketch_id_matches_mark(assignment["sketch_id"], header_mark):
                mismatches.append(
                    BeamMarkMismatch(
                        beam_mark=assignment["beam_mark"],
                        occurrence_id=assignment["occurrence_id"],
                        sketch_id=assignment["sketch_id"],
                        sketch_beam_mark=sketch_mark,
                    )
                )
        return mismatches

    @staticmethod
    def _sketch_id_matches_mark(sketch_id: str, beam_mark: str) -> bool:
        match = re.match(r"^(B\d+)_S\d+$", sketch_id, re.IGNORECASE)
        if match is None:
            return True
        return match.group(1).upper() == beam_mark.upper()

    @staticmethod
    def _owned_sketch_ids(
        ownership: List[EnrichedSketchOwnershipRecord],
    ) -> set[str]:
        owned: set[str] = set()
        for record in ownership:
            for audit in record["owned_sketches"]:
                owned.add(str(audit["sketch_id"]))
        return owned

    @staticmethod
    def _ownership_counts(
        ownership: List[EnrichedSketchOwnershipRecord],
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in ownership:
            for audit in record["owned_sketches"]:
                sketch_id = str(audit["sketch_id"])
                counts[sketch_id] = counts.get(sketch_id, 0) + 1
        return counts
