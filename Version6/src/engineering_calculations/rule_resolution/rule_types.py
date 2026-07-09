"""Resolved engineering rule type definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ResolvedEngineeringRule:
    """Rule resolution output without mathematical evaluation."""

    rule_source: str
    rule_name: str
    rule_reference: str
    rule_priority: int
    structural_code_reference: str
    general_notes_reference: str
    lookup_path: tuple[str, ...]


@dataclass(frozen=True)
class ResolvedLapRule(ResolvedEngineeringRule):
    """Resolved lap splice rule parameters."""

    lap_factor: float
    minimum_lap_mm: int
    reinforcement_position: str
    rule_description: str

    def to_inputs(self) -> dict[str, object]:
        return {
            "lap_factor": self.lap_factor,
            "minimum_lap_mm": self.minimum_lap_mm,
            "lap_rule_source": self.rule_source,
            "reinforcement_position": self.reinforcement_position,
        }


@dataclass(frozen=True)
class ResolvedCutLengthRule(ResolvedEngineeringRule):
    """Resolved cut length rule parameters without mathematical evaluation."""

    span_basis: str
    development_length_end_count: int
    hook_length_end_count: int
    lap_length_adjustment_count: int
    reinforcement_position: str
    reinforcement_role: str
    rule_description: str
    use_effective_span: bool = False

    def to_formula_spec(self) -> dict[str, object]:
        return {
            "span_basis": self.span_basis,
            "development_length_end_count": self.development_length_end_count,
            "hook_length_end_count": self.hook_length_end_count,
            "lap_length_adjustment_count": self.lap_length_adjustment_count,
            "use_effective_span": self.use_effective_span,
            "rule_source": self.rule_source,
            "rule_name": self.rule_name,
            "rule_reference": self.rule_reference,
        }


@dataclass(frozen=True)
class ResolvedShapeCodeRule(ResolvedEngineeringRule):
    """Resolved shape code rule parameters without classification."""

    shape_code: str
    shape_family: str
    bend_count: int
    hook_count: int
    closed_loop: bool
    open_loop: bool
    anchorage_configuration: str
    stirrup_classification: str
    link_classification: str
    main_bar_classification: str
    reinforcement_role: str
    rule_description: str

    def to_classification_spec(self) -> dict[str, object]:
        return {
            "shape_code": self.shape_code,
            "shape_family": self.shape_family,
            "bend_count": self.bend_count,
            "hook_count": self.hook_count,
            "closed_loop": self.closed_loop,
            "open_loop": self.open_loop,
            "anchorage_configuration": self.anchorage_configuration,
            "stirrup_classification": self.stirrup_classification,
            "link_classification": self.link_classification,
            "main_bar_classification": self.main_bar_classification,
            "reinforcement_role": self.reinforcement_role,
            "rule_source": self.rule_source,
            "rule_name": self.rule_name,
            "rule_reference": self.rule_reference,
        }


@dataclass(frozen=True)
class ResolvedBarIdentityRule(ResolvedEngineeringRule):
    """Resolved bar identity grouping rule parameters without identity assignment."""

    grouping_strategy: str
    equivalence_attributes: tuple[str, ...]
    include_support_configuration: bool
    include_geometry_signature: bool
    reinforcement_role: str
    rule_description: str

    def to_grouping_spec(self) -> dict[str, object]:
        return {
            "grouping_strategy": self.grouping_strategy,
            "equivalence_attributes": list(self.equivalence_attributes),
            "include_support_configuration": self.include_support_configuration,
            "include_geometry_signature": self.include_geometry_signature,
            "rule_source": self.rule_source,
            "rule_name": self.rule_name,
            "rule_reference": self.rule_reference,
        }


@dataclass(frozen=True)
class ResolvedBarGroupRule(ResolvedEngineeringRule):
    """Resolved bar group aggregation policy without group creation."""

    grouping_strategy: str
    group_by_identity: bool
    group_by_geometry: bool
    group_by_shape: bool
    group_by_cut_length: bool
    rule_description: str

    def to_grouping_spec(self) -> dict[str, object]:
        return {
            "grouping_strategy": self.grouping_strategy,
            "group_by_identity": self.group_by_identity,
            "group_by_geometry": self.group_by_geometry,
            "group_by_shape": self.group_by_shape,
            "group_by_cut_length": self.group_by_cut_length,
            "rule_source": self.rule_source,
            "rule_name": self.rule_name,
            "rule_reference": self.rule_reference,
        }


@dataclass(frozen=True)
class ResolvedBbsRule(ResolvedEngineeringRule):
    """Resolved BBS fabrication policy without schedule generation."""

    fabrication_mark_format: str
    schedule_numbering_policy: str
    schedule_ordering_policy: str
    naming_policy: str
    rule_description: str

    def to_schedule_spec(self) -> dict[str, object]:
        return {
            "fabrication_mark_format": self.fabrication_mark_format,
            "schedule_numbering_policy": self.schedule_numbering_policy,
            "schedule_ordering_policy": self.schedule_ordering_policy,
            "naming_policy": self.naming_policy,
            "rule_source": self.rule_source,
            "rule_name": self.rule_name,
            "rule_reference": self.rule_reference,
        }
