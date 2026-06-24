"""Phase D.1.7 — validate DIMENSION extraction and ownership integration."""

from typing import List, TypedDict

from src.annotations.dimension_annotation_integrator import (
    DimensionAssignment,
    DimensionAnnotationIntegrator,
)


class DimensionExtractionValidation(TypedDict):
    dimension_entities_found: int
    stirrup_annotations_found: int
    anchorage_annotations_found: int
    numeric_dimensions_found: int
    ownership_assigned: int
    ownership_unassigned: int
    status: str


class DimensionAnnotationValidator:
    """Summarize DIMENSION extraction counts and ownership assignment."""

    def validate(
        self,
        dimension_assignments: List[DimensionAssignment],
    ) -> DimensionExtractionValidation:
        stirrup = 0
        anchorage = 0
        numeric = 0
        assigned = 0
        unassigned = 0

        for assignment in dimension_assignments:
            category = DimensionAnnotationIntegrator.classify_dimension_category(
                assignment["dimension"]["text"]
            )
            if category == "STIRRUP":
                stirrup += 1
            elif category == "ANCHORAGE":
                anchorage += 1
            elif category == "NUMERIC_DIMENSION":
                numeric += 1

            if assignment["assigned"]:
                assigned += 1
            else:
                unassigned += 1

        status = "PASS"
        if (
            stirrup == 0
            or anchorage == 0
            or numeric == 0
        ):
            status = "FAIL"

        return DimensionExtractionValidation(
            dimension_entities_found=len(dimension_assignments),
            stirrup_annotations_found=stirrup,
            anchorage_annotations_found=anchorage,
            numeric_dimensions_found=numeric,
            ownership_assigned=assigned,
            ownership_unassigned=unassigned,
            status=status,
        )
