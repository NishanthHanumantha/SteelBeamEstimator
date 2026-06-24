"""Phase D.1.7B — validate engineering annotation filter outputs."""

from typing import Any, Dict, List, Set, TypedDict

from src.annotations.engineering_annotation_filter import GEOMETRY_QA_VALUES

REJECTED_MEASUREMENT_VALUES = frozenset({"687", "688", "530", "537"})


class EngineeringAnnotationValidation(TypedDict):
    total_input_annotations: int
    engineering_annotations: int
    geometry_dimensions: int
    rejected_measurements: int
    count_by_type: Dict[str, int]
    rejected_in_engineering: int
    geometry_in_engineering: int
    checks: Dict[str, bool]
    status: str


class EngineeringAnnotationValidator:
    """Validate filtered engineering dataset for Phase D.2 readiness."""

    def validate(
        self,
        summary: dict[str, Any],
        engineering: List[dict[str, Any]],
        geometry: List[dict[str, Any]],
        rejected: List[dict[str, Any]],
    ) -> EngineeringAnnotationValidation:
        eng_texts = self._collect_clean_texts(engineering)
        geo_texts = self._collect_clean_texts(geometry)
        rejected_texts = {str(item["clean_text"]) for item in rejected}

        rejected_in_engineering = sum(
            1 for text in eng_texts if text in REJECTED_MEASUREMENT_VALUES
        )
        geometry_in_engineering = sum(
            1 for text in eng_texts if text in GEOMETRY_QA_VALUES
        )

        count_by_type = summary.get("count_by_type", {})
        checks = {
            "engineering_annotations_gt_zero": summary["engineering_annotations"] > 0,
            "stirrup_gt_zero": int(count_by_type.get("STIRRUP", 0)) > 0,
            "anchorage_gt_zero": int(count_by_type.get("ANCHORAGE", 0)) > 0,
            "no_rejected_in_engineering": rejected_in_engineering == 0,
            "no_geometry_in_engineering": geometry_in_engineering == 0,
            "rejected_not_in_engineering": not any(
                text in eng_texts for text in REJECTED_MEASUREMENT_VALUES
            ),
            "geometry_not_in_engineering": not any(
                text in eng_texts for text in GEOMETRY_QA_VALUES
            ),
            "geometry_separate": not any(text in eng_texts for text in geo_texts),
        }

        status = "PASS" if all(checks.values()) else "FAIL"

        return EngineeringAnnotationValidation(
            total_input_annotations=int(summary["total_input_annotations"]),
            engineering_annotations=int(summary["engineering_annotations"]),
            geometry_dimensions=int(summary["geometry_dimensions"]),
            rejected_measurements=int(summary["rejected_measurements"]),
            count_by_type=dict(count_by_type),
            rejected_in_engineering=rejected_in_engineering,
            geometry_in_engineering=geometry_in_engineering,
            checks=checks,
            status=status,
        )

    @staticmethod
    def _collect_clean_texts(records: List[dict[str, Any]]) -> Set[str]:
        texts: Set[str] = set()
        for sketch_record in records:
            for item in sketch_record.get("annotations", []):
                texts.add(str(item["clean_text"]))
        return texts
