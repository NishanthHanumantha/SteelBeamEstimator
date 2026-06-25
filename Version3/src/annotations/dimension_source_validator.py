"""Phase D.1.7A — validate DIMENSION text source audit completeness."""

from typing import List, TypedDict

from src.annotations.dimension_source_auditor import (
    DimensionSourceRecord,
    RepeatedValueRecord,
    SourceSummary,
)

EXPECTED_D17_DIMENSION_COUNT = 88


class DimensionSourceValidation(TypedDict):
    total_audited: int
    expected_d17_count: int
    missing_handles: int
    duplicate_handles: int
    unclassified: int
    repeated_value_groups: int
    all_checks_passed: bool
    status: str


class DimensionSourceValidator:
    """Verify audit coverage and classification completeness."""

    def validate(
        self,
        records: List[DimensionSourceRecord],
        summary: SourceSummary,
        repeated_values: List[RepeatedValueRecord],
    ) -> DimensionSourceValidation:
        handles = [record["handle"] for record in records]
        unique_handles = set(handles)

        missing_handles = max(0, EXPECTED_D17_DIMENSION_COUNT - len(unique_handles))
        duplicate_handles = len(handles) - len(unique_handles)
        unclassified = sum(
            1
            for record in records
            if record["source_type"] not in {
                "ENGINEERING_TEXT",
                "MEASUREMENT_VALUE",
                "UNKNOWN_SOURCE",
            }
        )

        classified_total = (
            summary["engineering_text_count"]
            + summary["measurement_value_count"]
            + summary["unknown_source_count"]
        )
        all_classified = classified_total == len(records) and unclassified == 0

        all_checks_passed = (
            len(records) == EXPECTED_D17_DIMENSION_COUNT
            and missing_handles == 0
            and duplicate_handles == 0
            and all_classified
            and len(repeated_values) > 0
        )

        return DimensionSourceValidation(
            total_audited=len(records),
            expected_d17_count=EXPECTED_D17_DIMENSION_COUNT,
            missing_handles=missing_handles,
            duplicate_handles=duplicate_handles,
            unclassified=unclassified,
            repeated_value_groups=len(repeated_values),
            all_checks_passed=all_checks_passed,
            status="PASS" if all_checks_passed else "FAIL",
        )
