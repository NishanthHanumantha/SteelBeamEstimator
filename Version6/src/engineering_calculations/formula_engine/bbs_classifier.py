"""BBS classifier — pure schedule membership assignment only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Tuple

from src.engineering_calculations.bar_group.bar_group_types import BarGroupState
from src.engineering_calculations.rule_resolution.rule_types import ResolvedBbsRule


@dataclass(frozen=True)
class BbsClassificationInput:
    """Pure inputs for deterministic schedule membership assignment."""

    resolved_rule: ResolvedBbsRule
    group_records: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class BbsScheduleMembership:
    """Schedule membership output without registry IDs or fabrication marks."""

    bar_group_id: str
    engineering_group_id: str
    engineering_signature: str
    member_bar_ids: tuple[str, ...]
    member_identity_ids: tuple[str, ...]
    member_beams: tuple[str, ...]
    member_roles: tuple[str, ...]
    diameter_mm: int
    shape_code: str
    cut_length_mm: int
    geometry_signature: str
    support_configuration: str
    member_count: int


class BbsClassifier:
    """Assign deterministic schedule membership from engineering bar groups."""

    @classmethod
    def classify(
        cls,
        classification_input: BbsClassificationInput,
    ) -> Tuple[BbsScheduleMembership, ...]:
        calculated = [
            record
            for record in classification_input.group_records
            if record.get("determination_state") == BarGroupState.CALCULATED.value
        ]
        sorted_groups = sorted(
            calculated,
            key=lambda item: (
                str(item.get("engineering_signature", "")),
                str(item.get("engineering_group_id", "")),
            ),
        )
        memberships: List[BbsScheduleMembership] = []
        for record in sorted_groups:
            roles = record.get("member_roles") or []
            primary_role = str(roles[0]) if roles else ""
            memberships.append(
                BbsScheduleMembership(
                    bar_group_id=str(record.get("bar_group_id", "")),
                    engineering_group_id=str(record.get("engineering_group_id", "")),
                    engineering_signature=str(record.get("engineering_signature", "")),
                    member_bar_ids=tuple(str(item) for item in (record.get("member_bar_ids") or [])),
                    member_identity_ids=tuple(
                        str(item) for item in (record.get("member_identity_ids") or [])
                    ),
                    member_beams=tuple(str(item) for item in (record.get("member_beams") or [])),
                    member_roles=tuple(str(item) for item in roles),
                    diameter_mm=int(record.get("diameter") or 0),
                    shape_code=str(record.get("shape_code") or ""),
                    cut_length_mm=int(record.get("cut_length") or 0),
                    geometry_signature=str(record.get("geometry_signature") or ""),
                    support_configuration=str(record.get("support_configuration") or ""),
                    member_count=int(record.get("member_count") or 0),
                )
            )
        return tuple(memberships)
