"""Validate annotation type classification distribution."""

from typing import Any, Dict, List, TypedDict

AnnotationType = str

PASS_UNKNOWN_MAX_PCT = 10.0
FAIL_UNKNOWN_MAX_PCT = 25.0

ALL_TYPES: List[AnnotationType] = [
    "BAR",
    "STIRRUP",
    "DIMENSION",
    "ANCHORAGE",
    "SIDE_FACE_REINF",
    "NOTE",
    "UNKNOWN",
]


class AnnotationTypeValidation(TypedDict):
    total_annotations: int
    count_by_type: Dict[str, int]
    percentage_by_type: Dict[str, float]
    unknown_count: int
    unknown_percentage: float
    status: str


class AnnotationTypeValidator:
    """Summarize classification counts and determine PASS/WARN/FAIL."""

    def validate(self, classified_records: List[dict[str, Any]]) -> AnnotationTypeValidation:
        counts: Dict[str, int] = {type_name: 0 for type_name in ALL_TYPES}
        for record in classified_records:
            annotation_type = str(record.get("annotation_type", "UNKNOWN"))
            if annotation_type not in counts:
                annotation_type = "UNKNOWN"
            counts[annotation_type] += 1

        total = len(classified_records)
        percentages: Dict[str, float] = {}
        for type_name in ALL_TYPES:
            count = counts[type_name]
            percentages[type_name] = round((count / total) * 100.0, 2) if total else 0.0

        unknown_count = counts["UNKNOWN"]
        unknown_pct = percentages["UNKNOWN"]
        status = self._status_for_unknown(unknown_pct)

        return AnnotationTypeValidation(
            total_annotations=total,
            count_by_type=counts,
            percentage_by_type=percentages,
            unknown_count=unknown_count,
            unknown_percentage=unknown_pct,
            status=status,
        )

    def build_summary_text(self, validation: AnnotationTypeValidation) -> str:
        lines = [
            "==================================================",
            "Annotation Type Classification Summary",
            "==================================================",
            "",
            f"Total annotations: {validation['total_annotations']}",
            "",
        ]
        for type_name in ALL_TYPES:
            count = validation["count_by_type"][type_name]
            lines.append(f"{type_name}: {count}")
        lines.extend(
            [
                "",
                f"UNKNOWN %: {validation['unknown_percentage']}",
                "",
                f"Validation: {validation['status']}",
                "==================================================",
            ]
        )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _status_for_unknown(unknown_percentage: float) -> str:
        if unknown_percentage <= PASS_UNKNOWN_MAX_PCT:
            return "PASS"
        if unknown_percentage <= FAIL_UNKNOWN_MAX_PCT:
            return "WARN"
        return "FAIL"
