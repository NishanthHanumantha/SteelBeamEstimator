"""Shape code classifier — pure engineering classification only."""

from __future__ import annotations

from dataclasses import dataclass

from src.engineering_calculations.rule_resolution.rule_types import ResolvedShapeCodeRule
from src.engineering_calculations.shape_code_types import (
    FAMILY_CLOSED_STIRRUP,
    FAMILY_CRANKED_BAR,
    FAMILY_L_BAR,
    FAMILY_LINK,
    FAMILY_OPEN_STIRRUP,
    FAMILY_SIDE_BAR,
    FAMILY_STRAIGHT,
    FAMILY_U_BAR,
    INTERNAL_CODE_CRANK,
    INTERNAL_CODE_L,
    INTERNAL_CODE_LINK,
    INTERNAL_CODE_OPEN_STIRRUP,
    INTERNAL_CODE_SIDE,
    INTERNAL_CODE_STIRRUP,
    INTERNAL_CODE_STRAIGHT,
    INTERNAL_CODE_U,
)


@dataclass(frozen=True)
class ShapeCodeClassificationInput:
    """Pure numeric and metadata inputs for shape code classification."""

    reinforcement_role: str
    bar_type: str
    hook_count: int
    bend_count: int
    closed_loop: bool
    open_loop: bool
    hook_angle: int
    cut_length_mm: int
    clear_span_mm: int
    resolved_rule: ResolvedShapeCodeRule


@dataclass(frozen=True)
class ShapeCodeClassificationResult:
    """Classification output."""

    shape_code: str
    shape_family: str


class ShapeCodeClassifier:
    """Classify reinforcement shape from resolved rule and numeric inputs only."""

    @classmethod
    def classify(cls, classification_input: ShapeCodeClassificationInput) -> ShapeCodeClassificationResult:
        rule = classification_input.resolved_rule
        role = str(classification_input.reinforcement_role).upper()

        if rule.link_classification == "OPEN" or role == "LINK_BAR":
            return ShapeCodeClassificationResult(
                shape_code=INTERNAL_CODE_LINK,
                shape_family=FAMILY_LINK,
            )
        if rule.closed_loop or rule.stirrup_classification == "CLOSED":
            return ShapeCodeClassificationResult(
                shape_code=INTERNAL_CODE_STIRRUP,
                shape_family=FAMILY_CLOSED_STIRRUP,
            )
        if rule.open_loop or role == "SPACER":
            return ShapeCodeClassificationResult(
                shape_code=INTERNAL_CODE_OPEN_STIRRUP,
                shape_family=FAMILY_OPEN_STIRRUP,
            )
        if role == "SIDE_BAR" or rule.shape_family == "SIDE_BAR":
            return ShapeCodeClassificationResult(
                shape_code=INTERNAL_CODE_SIDE,
                shape_family=FAMILY_SIDE_BAR,
            )
        if rule.bend_count >= 2 and classification_input.hook_count >= 2:
            return ShapeCodeClassificationResult(
                shape_code=INTERNAL_CODE_U,
                shape_family=FAMILY_U_BAR,
            )
        if rule.bend_count >= 1 and classification_input.hook_count == 1:
            return ShapeCodeClassificationResult(
                shape_code=INTERNAL_CODE_L,
                shape_family=FAMILY_L_BAR,
            )
        if role == "STARTER" and classification_input.hook_angle == 135:
            return ShapeCodeClassificationResult(
                shape_code=INTERNAL_CODE_CRANK,
                shape_family=FAMILY_CRANKED_BAR,
            )
        return ShapeCodeClassificationResult(
            shape_code=INTERNAL_CODE_STRAIGHT,
            shape_family=FAMILY_STRAIGHT,
        )
