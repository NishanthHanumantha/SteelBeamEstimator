"""Bar identity classifier — pure deterministic identity assignment only."""

from __future__ import annotations

from dataclasses import dataclass

from src.engineering_calculations.bar_identity.bar_identity_types import (
    format_bar_mark,
    format_engineering_bar_id,
    format_engineering_group_id,
)
from src.engineering_calculations.rule_resolution.rule_types import ResolvedBarIdentityRule


@dataclass(frozen=True)
class BarIdentityClassificationInput:
    """Pure inputs for deterministic bar identity assignment."""

    bar_id: str
    equivalence_signature: str
    identity_sequence: int
    group_sequence: int
    instance_index_in_group: int
    group_member_count: int
    resolved_rule: ResolvedBarIdentityRule


@dataclass(frozen=True)
class BarIdentityClassificationResult:
    """Classification output."""

    engineering_bar_id: str
    engineering_bar_mark: str
    engineering_group_id: str
    instance_index_in_group: int
    group_member_count: int
    is_duplicate: bool


class BarIdentityClassifier:
    """Assign deterministic engineering identities from resolved inputs only."""

    @classmethod
    def classify(
        cls,
        classification_input: BarIdentityClassificationInput,
    ) -> BarIdentityClassificationResult:
        return BarIdentityClassificationResult(
            engineering_bar_id=format_engineering_bar_id(
                int(classification_input.identity_sequence)
            ),
            engineering_bar_mark=format_bar_mark(
                int(classification_input.identity_sequence)
            ),
            engineering_group_id=format_engineering_group_id(
                int(classification_input.group_sequence)
            ),
            instance_index_in_group=int(classification_input.instance_index_in_group),
            group_member_count=int(classification_input.group_member_count),
            is_duplicate=int(classification_input.group_member_count) > 1,
        )
