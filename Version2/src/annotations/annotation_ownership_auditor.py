"""Phase D.1.1 — audit annotation-to-sketch assignment quality (read-only)."""

import math
from typing import Any, Dict, List, Tuple, TypedDict

from loguru import logger

HIGH_CONFIDENCE_MAX_MM = 1500.0
MEDIUM_CONFIDENCE_MAX_MM = 4000.0
LOW_CONFIDENCE_MAX_MM = 8000.0


class AnnotationOwnershipAuditRecord(TypedDict):
    beam_mark: str
    sketch_id: str
    annotation: str
    x: float
    y: float
    distance_mm: float
    confidence: str


class SuspiciousAnnotation(TypedDict):
    beam_mark: str
    sketch_id: str
    annotation: str
    x: float
    y: float
    distance_mm: float


class AnnotationOwnershipValidation(TypedDict):
    total_annotations: int
    high_confidence: int
    medium_confidence: int
    low_confidence: int
    suspicious: int
    suspicious_annotations: List[SuspiciousAnnotation]
    status: str


class AnnotationOwnershipAuditor:
    """Measure distance from each raw annotation to its assigned sketch centroid."""

    def audit(
        self,
        annotations_raw: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
    ) -> List[AnnotationOwnershipAuditRecord]:
        sketch_lookup = {str(sketch["sketch_id"]): sketch for sketch in sketches}
        records: List[AnnotationOwnershipAuditRecord] = []

        for sketch_record in annotations_raw:
            beam_mark = str(sketch_record["beam_mark"])
            sketch_id = str(sketch_record["sketch_id"])
            sketch = sketch_lookup.get(sketch_id)
            if sketch is None:
                logger.warning("Sketch {} not found in geometry — skipping audit", sketch_id)
                continue

            cx, cy = self._sketch_centroid(sketch)
            for item in sketch_record.get("texts", []):
                x = float(item["x"])
                y = float(item["y"])
                text = str(item["text"])
                distance_mm = round(self._distance(x, y, cx, cy), 1)
                records.append(
                    AnnotationOwnershipAuditRecord(
                        beam_mark=beam_mark,
                        sketch_id=sketch_id,
                        annotation=text,
                        x=round(x, 1),
                        y=round(y, 1),
                        distance_mm=distance_mm,
                        confidence=self._classify_confidence(distance_mm),
                    )
                )

        records.sort(
            key=lambda record: (
                record["beam_mark"],
                record["sketch_id"],
                -record["y"],
                record["x"],
            )
        )
        logger.info("Audited {} annotation ownership record(s)", len(records))
        return records

    def build_validation(
        self, audit_records: List[AnnotationOwnershipAuditRecord]
    ) -> AnnotationOwnershipValidation:
        high = sum(1 for r in audit_records if r["confidence"] == "HIGH")
        medium = sum(1 for r in audit_records if r["confidence"] == "MEDIUM")
        low = sum(1 for r in audit_records if r["confidence"] == "LOW")
        suspicious_records = [r for r in audit_records if r["confidence"] == "SUSPICIOUS"]
        suspicious_count = len(suspicious_records)
        total = len(audit_records)

        suspicious_list: List[SuspiciousAnnotation] = [
            SuspiciousAnnotation(
                beam_mark=r["beam_mark"],
                sketch_id=r["sketch_id"],
                annotation=r["annotation"],
                x=r["x"],
                y=r["y"],
                distance_mm=r["distance_mm"],
            )
            for r in sorted(
                suspicious_records,
                key=lambda item: -item["distance_mm"],
            )
        ]

        suspicious_ratio = suspicious_count / total if total else 0.0
        if suspicious_ratio <= 0.10:
            status = "PASS"
        elif suspicious_ratio <= 0.25:
            status = "PASS_WITH_WARNINGS"
        else:
            status = "FAIL"

        return AnnotationOwnershipValidation(
            total_annotations=total,
            high_confidence=high,
            medium_confidence=medium,
            low_confidence=low,
            suspicious=suspicious_count,
            suspicious_annotations=suspicious_list,
            status=status,
        )

    def build_summary_text(
        self,
        audit_records: List[AnnotationOwnershipAuditRecord],
        limit: int = 20,
    ) -> str:
        sorted_records = sorted(
            audit_records,
            key=lambda record: -record["distance_mm"],
        )
        lines = [
            "Annotation Ownership Audit — Top Distant Assignments",
            "=" * 72,
            f"{'Beam':<8} {'Sketch':<12} {'Annotation':<32} {'Distance(mm)':>12}",
            "-" * 72,
        ]
        for record in sorted_records[:limit]:
            annotation = self._summary_annotation(record["annotation"])
            lines.append(
                f"{record['beam_mark']:<8} "
                f"{record['sketch_id']:<12} "
                f"{annotation:<32} "
                f"{record['distance_mm']:>12.1f}"
            )
        lines.append("-" * 72)
        lines.append(f"Total annotations audited: {len(audit_records)}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _sketch_centroid(sketch: dict[str, Any]) -> Tuple[float, float]:
        bbox = sketch["bbox"]
        cx = (float(bbox["xmin"]) + float(bbox["xmax"])) / 2.0
        cy = (float(bbox["ymin"]) + float(bbox["ymax"])) / 2.0
        return cx, cy

    @staticmethod
    def _distance(x: float, y: float, cx: float, cy: float) -> float:
        return math.hypot(x - cx, y - cy)

    @staticmethod
    def _classify_confidence(distance_mm: float) -> str:
        if distance_mm <= HIGH_CONFIDENCE_MAX_MM:
            return "HIGH"
        if distance_mm <= MEDIUM_CONFIDENCE_MAX_MM:
            return "MEDIUM"
        if distance_mm <= LOW_CONFIDENCE_MAX_MM:
            return "LOW"
        return "SUSPICIOUS"

    @staticmethod
    def _summary_annotation(text: str) -> str:
        cleaned = text.replace("\\P", " ").replace("\n", " ").strip()
        if cleaned.startswith("\\A1;"):
            cleaned = cleaned[4:]
        if len(cleaned) > 32:
            return cleaned[:29] + "..."
        return cleaned
