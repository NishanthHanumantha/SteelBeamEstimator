"""Bar group classifier — pure group membership assignment only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Tuple

from src.engineering_calculations.bar_group.bar_group_types import (
    compute_engineering_signature_from_inputs,
)
from src.engineering_calculations.rule_resolution.rule_types import ResolvedBarGroupRule


@dataclass(frozen=True)
class BarGroupClassificationInput:
    """Pure inputs for deterministic group membership assignment."""

    resolved_rule: ResolvedBarGroupRule
    identity_records: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class BarGroupMembership:
    """Group membership output without registry IDs."""

    engineering_signature: str
    member_bar_ids: tuple[str, ...]
    member_identity_ids: tuple[str, ...]
    member_beams: tuple[str, ...]
    member_roles: tuple[str, ...]
    diameter_mm: int
    shape_code: str
    cut_length_mm: int
    hook_length_mm: int
    development_length_mm: int
    lap_length_mm: int
    geometry_signature: str
    support_configuration: str


class BarGroupClassifier:
    """Assign deterministic group membership from resolved rules and identity records."""

    @classmethod
    def classify(
        cls,
        classification_input: BarGroupClassificationInput,
    ) -> Tuple[BarGroupMembership, ...]:
        clusters: dict[str, List[dict[str, Any]]] = {}
        for record in classification_input.identity_records:
            inputs = dict(record.get("classification_inputs") or {})
            if not inputs.get("hook_length_mm"):
                inputs.setdefault("hook_length_mm", 0)
            if not inputs.get("development_length_mm"):
                inputs.setdefault("development_length_mm", 0)
            if not inputs.get("lap_length_mm"):
                inputs.setdefault("lap_length_mm", 0)
            inputs.setdefault("reinforcement_role", record.get("reinforcement_role"))
            inputs.setdefault("bar_diameter_mm", record.get("bar_diameter_mm"))
            inputs.setdefault("shape_code", record.get("shape_code"))
            inputs.setdefault("cut_length_mm", record.get("cut_length_mm"))
            signature = compute_engineering_signature_from_inputs(inputs)
            clusters.setdefault(signature, []).append(record)

        memberships: List[BarGroupMembership] = []
        for signature in sorted(clusters.keys()):
            members = sorted(
                clusters[signature],
                key=lambda item: str(item.get("bar_id", "")),
            )
            representative = members[0]
            rep_inputs = dict(representative.get("classification_inputs") or {})
            memberships.append(
                BarGroupMembership(
                    engineering_signature=signature,
                    member_bar_ids=tuple(
                        str(item.get("bar_id", "")) for item in members if item.get("bar_id")
                    ),
                    member_identity_ids=tuple(
                        str(item.get("bar_identity_id", ""))
                        for item in members
                        if item.get("bar_identity_id")
                    ),
                    member_beams=tuple(
                        sorted({str(item.get("beam_id", "")) for item in members if item.get("beam_id")})
                    ),
                    member_roles=tuple(
                        sorted(
                            {
                                str(item.get("reinforcement_role", ""))
                                for item in members
                                if item.get("reinforcement_role")
                            }
                        )
                    ),
                    diameter_mm=int(
                        rep_inputs.get("bar_diameter_mm")
                        or representative.get("bar_diameter_mm")
                        or 0
                    ),
                    shape_code=str(
                        rep_inputs.get("shape_code") or representative.get("shape_code") or ""
                    ),
                    cut_length_mm=int(
                        rep_inputs.get("cut_length_mm")
                        or representative.get("cut_length_mm")
                        or 0
                    ),
                    hook_length_mm=int(rep_inputs.get("hook_length_mm") or 0),
                    development_length_mm=int(rep_inputs.get("development_length_mm") or 0),
                    lap_length_mm=int(rep_inputs.get("lap_length_mm") or 0),
                    geometry_signature=str(rep_inputs.get("geometry_signature", "")),
                    support_configuration=str(rep_inputs.get("support_configuration", "")),
                )
            )
        return tuple(memberships)
