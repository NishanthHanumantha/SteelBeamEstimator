"""Cut length rule resolver — rule selection only, no mathematics."""

from __future__ import annotations

from typing import Any, List, Optional

from src.engineering_calculations.cut_length_types import (
    COMPRESSION_POSITION,
    MAIN_BAR_ROLES,
    RULE_SOURCE_GENERAL_NOTES,
    SPAN_BASIS_CLEAR_SPAN,
    SPAN_BASIS_SECTION_PERIMETER,
    TENSION_POSITION,
    TRANSVERSE_ROLES,
)
from src.engineering_calculations.rule_resolution.rule_types import ResolvedCutLengthRule
from src.general_notes.engineering_rule_cache import EngineeringRuleCache


class CutLengthRuleResolver:
    """Resolve applicable cut length rules from General Notes / structural code cache."""

    RULE_NAME_MAIN_TENSION = "MAIN_TENSION_CUT_LENGTH"
    RULE_NAME_TRANSVERSE = "TRANSVERSE_CUT_LENGTH"
    RULE_NAME_COMPRESSION = "COMPRESSION_MAIN_CUT_LENGTH"

    def __init__(self, cache: EngineeringRuleCache) -> None:
        self._cache = cache
        self._anchorage_rules = self._collect_anchorage_rules()

    def resolve(
        self,
        bar: dict[str, Any],
        context: dict[str, Any],
    ) -> ResolvedCutLengthRule:
        role = str(bar.get("role") or "UNKNOWN").upper()
        position = self._resolve_reinforcement_position(bar, context, role)
        hook_rule = self._find_anchorage_rule("HOOK_ANCHORAGE", "STANDARD HOOKS")
        tension_rule = self._find_anchorage_rule("TENSION_LD", "TENSION REINFORCEMENTS")
        compression_rule = self._find_anchorage_rule("COMPRESSION_LD", "COMPRESSION")

        if role in TRANSVERSE_ROLES:
            return self._resolve_transverse_rule(role, hook_rule)
        if position == COMPRESSION_POSITION:
            return self._resolve_compression_rule(role, compression_rule)
        return self._resolve_main_tension_rule(role, hook_rule, tension_rule)

    def _resolve_main_tension_rule(
        self,
        role: str,
        hook_rule: Optional[dict[str, Any]],
        tension_rule: Optional[dict[str, Any]],
    ) -> ResolvedCutLengthRule:
        hook_description = str((hook_rule or {}).get("description", ""))
        tension_description = str((tension_rule or {}).get("description", ""))
        rule_source = str(
            ((hook_rule or {}).get("provenance") or {}).get("source")
            or RULE_SOURCE_GENERAL_NOTES
        )
        rule_reference = hook_description or tension_description
        rule_name = f"{role}_CUT_LENGTH" if role in MAIN_BAR_ROLES else self.RULE_NAME_MAIN_TENSION
        return ResolvedCutLengthRule(
            span_basis=SPAN_BASIS_CLEAR_SPAN,
            development_length_end_count=2,
            hook_length_end_count=2,
            lap_length_adjustment_count=0,
            rule_source=rule_source,
            rule_name=rule_name,
            rule_reference=rule_reference,
            rule_priority=1,
            structural_code_reference="IS456_ANCHORAGE",
            general_notes_reference=rule_reference,
            lookup_path=(
                "structural_detailing_rules",
                "anchorage_rules",
                "HOOK_ANCHORAGE",
                "TENSION_LD",
            ),
            reinforcement_position=TENSION_POSITION,
            reinforcement_role=role,
            rule_description=(
                "Beam main bar cut length uses clear span with development length and "
                "standard hook anchorage at both supports."
            ),
            use_effective_span=False,
        )

    def _resolve_compression_rule(
        self,
        role: str,
        compression_rule: Optional[dict[str, Any]],
    ) -> ResolvedCutLengthRule:
        description = str((compression_rule or {}).get("description", ""))
        rule_source = str(
            ((compression_rule or {}).get("provenance") or {}).get("source")
            or RULE_SOURCE_GENERAL_NOTES
        )
        return ResolvedCutLengthRule(
            span_basis=SPAN_BASIS_CLEAR_SPAN,
            development_length_end_count=2,
            hook_length_end_count=0,
            lap_length_adjustment_count=0,
            rule_source=rule_source,
            rule_name=self.RULE_NAME_COMPRESSION,
            rule_reference=description,
            rule_priority=2,
            structural_code_reference="IS456_COMPRESSION_LD",
            general_notes_reference=description,
            lookup_path=(
                "structural_detailing_rules",
                "anchorage_rules",
                "COMPRESSION_LD",
            ),
            reinforcement_position=COMPRESSION_POSITION,
            reinforcement_role=role,
            rule_description=(
                "Compression reinforcement cut length uses clear span with straight "
                "development length and no hook allowance."
            ),
            use_effective_span=False,
        )

    def _resolve_transverse_rule(
        self,
        role: str,
        hook_rule: Optional[dict[str, Any]],
    ) -> ResolvedCutLengthRule:
        description = str((hook_rule or {}).get("description", ""))
        rule_source = str(
            ((hook_rule or {}).get("provenance") or {}).get("source")
            or RULE_SOURCE_GENERAL_NOTES
        )
        return ResolvedCutLengthRule(
            span_basis=SPAN_BASIS_SECTION_PERIMETER,
            development_length_end_count=0,
            hook_length_end_count=2,
            lap_length_adjustment_count=0,
            rule_source=rule_source,
            rule_name=self.RULE_NAME_TRANSVERSE,
            rule_reference=description or "TRANSVERSE_REINFORCEMENT_PERIMETER",
            rule_priority=3,
            structural_code_reference="",
            general_notes_reference=description,
            lookup_path=(
                "structural_detailing_rules",
                "anchorage_rules",
                "TRANSVERSE_CUT_LENGTH",
            ),
            reinforcement_position=TENSION_POSITION,
            reinforcement_role=role,
            rule_description=(
                "Transverse reinforcement cut length uses beam section perimeter with "
                "hook allowances at closed stirrup ends."
            ),
            use_effective_span=False,
        )

    def _collect_anchorage_rules(self) -> List[dict[str, Any]]:
        structural = self._cache.model.get("structural_detailing_rules", {})
        rules = list(structural.get("anchorage_rules", []))
        rules.extend(self._cache.model.get("anchorage_rules", []))
        return rules

    def _find_anchorage_rule(
        self,
        rule_type: str,
        needle: str,
    ) -> Optional[dict[str, Any]]:
        needle_upper = needle.upper()
        for rule in self._anchorage_rules:
            if str(rule.get("rule_type", "")).upper() == rule_type.upper():
                return rule
        for rule in self._anchorage_rules:
            description = str(rule.get("description", "")).upper()
            if needle_upper in description:
                return rule
        return None

    @staticmethod
    def _resolve_reinforcement_position(
        bar: dict[str, Any],
        context: dict[str, Any],
        role: str,
    ) -> str:
        if role in TRANSVERSE_ROLES:
            return TENSION_POSITION
        compression_roles = {"COMPRESSION_BAR", "COMPRESSION"}
        if role in compression_roles:
            return COMPRESSION_POSITION
        position = str(bar.get("position") or context.get("position") or "").upper()
        if "COMPRESSION" in position:
            return COMPRESSION_POSITION
        return TENSION_POSITION
