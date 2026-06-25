"""Phase C.5.1+ — audit metrics for sketch ownership (no assignment changes)."""

import math
from typing import Any, List, Tuple, TypedDict

from src.grid.sketch_ownership_builder import SketchOwnershipRecord
from src.grid.header_occurrence_exporter import HeaderOccurrenceRecord

HIGH_CONFIDENCE_MAX_MM = 1500.0
MEDIUM_CONFIDENCE_MAX_MM = 4000.0
LONG_DISTANCE_WARNING_MM = 10000.0


class OwnedSketchAudit(TypedDict):
    sketch_id: str
    distance_mm: float
    confidence: str


class EnrichedSketchOwnershipRecord(TypedDict):
    beam_mark: str
    occurrence_id: int
    owned_sketches: List[OwnedSketchAudit]


class OwnershipWarning(TypedDict):
    type: str
    beam_mark: str
    occurrence_id: int
    sketch_id: str
    distance_mm: float


class OwnershipAuditStats(TypedDict):
    total_assignments: int
    high_confidence: int
    medium_confidence: int
    low_confidence: int
    avg_assignment_distance_mm: float
    max_assignment_distance_mm: float


class OwnershipAuditSummary(TypedDict):
    ownership_status: str
    audit_status: str
    total_assignments: int
    high_confidence: int
    medium_confidence: int
    low_confidence: int
    warnings: int
    orphan_sketches: int
    multi_owned_sketches: int
    beam_mark_mismatches: int


class SketchOwnershipAuditor:
    """Compute distance, confidence, and statistics for existing ownership assignments."""

    def enrich_ownership(
        self,
        ownership: List[SketchOwnershipRecord],
        occurrences: List[HeaderOccurrenceRecord],
        sketches: List[dict[str, Any]],
    ) -> Tuple[List[EnrichedSketchOwnershipRecord], List[OwnedSketchAudit]]:
        occurrence_lookup = {
            (occ["beam_mark"], occ["occurrence_id"]): occ for occ in occurrences
        }
        sketch_lookup = {str(sketch["sketch_id"]): sketch for sketch in sketches}

        enriched: List[EnrichedSketchOwnershipRecord] = []
        all_audits: List[OwnedSketchAudit] = []

        for record in ownership:
            mark = record["beam_mark"]
            occurrence_id = record["occurrence_id"]
            occurrence = occurrence_lookup.get((mark, occurrence_id))
            owned_audits: List[OwnedSketchAudit] = []

            for sketch_id in record["owned_sketches"]:
                sketch = sketch_lookup.get(str(sketch_id))
                if occurrence is None or sketch is None:
                    continue
                audit = self._audit_sketch(
                    str(sketch_id),
                    float(occurrence["x"]),
                    float(occurrence["y"]),
                    sketch,
                )
                owned_audits.append(audit)
                all_audits.append(audit)

            enriched.append(
                EnrichedSketchOwnershipRecord(
                    beam_mark=mark,
                    occurrence_id=occurrence_id,
                    owned_sketches=owned_audits,
                )
            )

        return enriched, all_audits

    def compute_stats(self, audits: List[OwnedSketchAudit]) -> OwnershipAuditStats:
        if not audits:
            return OwnershipAuditStats(
                total_assignments=0,
                high_confidence=0,
                medium_confidence=0,
                low_confidence=0,
                avg_assignment_distance_mm=0.0,
                max_assignment_distance_mm=0.0,
            )

        distances = [audit["distance_mm"] for audit in audits]
        return OwnershipAuditStats(
            total_assignments=len(audits),
            high_confidence=sum(1 for a in audits if a["confidence"] == "HIGH"),
            medium_confidence=sum(1 for a in audits if a["confidence"] == "MEDIUM"),
            low_confidence=sum(1 for a in audits if a["confidence"] == "LOW"),
            avg_assignment_distance_mm=round(sum(distances) / len(distances), 1),
            max_assignment_distance_mm=round(max(distances), 1),
        )

    def compute_distance_distribution(
        self, audits: List[OwnedSketchAudit]
    ) -> dict[str, int]:
        distribution = {
            "0_1500": 0,
            "1500_4000": 0,
            "4000_8000": 0,
            "8000_plus": 0,
        }
        for audit in audits:
            distance = audit["distance_mm"]
            if distance <= HIGH_CONFIDENCE_MAX_MM:
                distribution["0_1500"] += 1
            elif distance <= MEDIUM_CONFIDENCE_MAX_MM:
                distribution["1500_4000"] += 1
            elif distance <= 8000.0:
                distribution["4000_8000"] += 1
            else:
                distribution["8000_plus"] += 1
        return distribution

    def find_long_distance_warnings(
        self,
        ownership: List[EnrichedSketchOwnershipRecord],
    ) -> List[OwnershipWarning]:
        warnings: List[OwnershipWarning] = []
        for record in ownership:
            for audit in record["owned_sketches"]:
                if audit["distance_mm"] > LONG_DISTANCE_WARNING_MM:
                    warnings.append(
                        OwnershipWarning(
                            type="LONG_DISTANCE",
                            beam_mark=record["beam_mark"],
                            occurrence_id=record["occurrence_id"],
                            sketch_id=audit["sketch_id"],
                            distance_mm=audit["distance_mm"],
                        )
                    )
        warnings.sort(
            key=lambda item: (
                item["beam_mark"],
                item["occurrence_id"],
                item["sketch_id"],
            )
        )
        return warnings

    def build_summary(
        self,
        ownership_status: str,
        audit_status: str,
        stats: OwnershipAuditStats,
        warnings: List[OwnershipWarning],
        orphan_count: int,
        multi_owned_count: int,
        beam_mark_mismatch_count: int,
    ) -> OwnershipAuditSummary:
        return OwnershipAuditSummary(
            ownership_status=ownership_status,
            audit_status=audit_status,
            total_assignments=stats["total_assignments"],
            high_confidence=stats["high_confidence"],
            medium_confidence=stats["medium_confidence"],
            low_confidence=stats["low_confidence"],
            warnings=len(warnings),
            orphan_sketches=orphan_count,
            multi_owned_sketches=multi_owned_count,
            beam_mark_mismatches=beam_mark_mismatch_count,
        )

    def _audit_sketch(
        self,
        sketch_id: str,
        header_x: float,
        header_y: float,
        sketch: dict[str, Any],
    ) -> OwnedSketchAudit:
        distance_mm = self._assignment_distance(header_x, header_y, sketch)
        return OwnedSketchAudit(
            sketch_id=sketch_id,
            distance_mm=distance_mm,
            confidence=self._classify_confidence(distance_mm),
        )

    @staticmethod
    def _assignment_distance(
        header_x: float,
        header_y: float,
        sketch: dict[str, Any],
    ) -> float:
        bbox = sketch["bbox"]
        cx = (float(bbox["xmin"]) + float(bbox["xmax"])) / 2.0
        cy = (float(bbox["ymin"]) + float(bbox["ymax"])) / 2.0
        return round(math.hypot(header_x - cx, header_y - cy), 1)

    @staticmethod
    def _classify_confidence(distance_mm: float) -> str:
        if distance_mm <= HIGH_CONFIDENCE_MAX_MM:
            return "HIGH"
        if distance_mm <= MEDIUM_CONFIDENCE_MAX_MM:
            return "MEDIUM"
        return "LOW"
