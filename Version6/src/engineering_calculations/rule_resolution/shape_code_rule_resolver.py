"""Shape code rule resolver — rule selection only, no classification."""

from __future__ import annotations

from typing import Any, List, Optional

from src.engineering_calculations.rule_resolution.rule_types import ResolvedShapeCodeRule
from src.engineering_calculations.shape_code_types import (
    MAIN_BAR_ROLES,
    RULE_SOURCE_GENERAL_NOTES,
    SIDE_BAR_ROLES,
    TRANSVERSE_ROLES,
)
from src.general_notes.engineering_rule_cache import EngineeringRuleCache


class ShapeCodeRuleResolver:
    """Resolve applicable shape classification rules from General Notes / structural cache."""

    RULE_NAME_MAIN = "MAIN_BAR_SHAPE"
    RULE_NAME_TRANSVERSE = "TRANSVERSE_SHAPE"
    RULE_NAME_SIDE = "SIDE_BAR_SHAPE"
    RULE_NAME_LINK = "LINK_SHAPE"

    def __init__(self, cache: EngineeringRuleCache) -> None:
        self._cache = cache
        self._bend_rules = self._collect_bend_rules()
        self._anchorage_rules = self._collect_anchorage_rules()

    def resolve(
        self,
        bar: dict[str, Any],
        context: dict[str, Any],
    ) -> ResolvedShapeCodeRule:
        role = str(bar.get("role") or "UNKNOWN").upper()
        hook_rule = self._find_anchorage_rule("HOOK_ANCHORAGE", "STANDARD HOOKS")
        bend_rule = self._find_bend_rule("BEND_MULTIPLIER")
        hook_description = str((hook_rule or {}).get("description", ""))
        bend_description = str((bend_rule or {}).get("description", ""))
        rule_source = str(
            ((hook_rule or {}).get("provenance") or {}).get("source")
            or RULE_SOURCE_GENERAL_NOTES
        )

        if role in TRANSVERSE_ROLES:
            return self._resolve_transverse_rule(role, hook_rule, bend_rule, rule_source)
        if role in SIDE_BAR_ROLES:
            return self._resolve_side_rule(role, hook_rule, rule_source)
        if role in MAIN_BAR_ROLES:
            return self._resolve_main_rule(role, hook_rule, bend_rule, rule_source)
        return self._resolve_default_rule(role, hook_rule, bend_rule, rule_source)

    def _resolve_main_rule(
        self,
        role: str,
        hook_rule: Optional[dict[str, Any]],
        bend_rule: Optional[dict[str, Any]],
        rule_source: str,
    ) -> ResolvedShapeCodeRule:
        hook_description = str((hook_rule or {}).get("description", ""))
        bend_description = str((bend_rule or {}).get("description", ""))
        return ResolvedShapeCodeRule(
            shape_code=role,
            shape_family="MAIN_BAR",
            bend_count=0,
            hook_count=2,
            closed_loop=False,
            open_loop=False,
            anchorage_configuration="DOUBLE_HOOK",
            stirrup_classification="NONE",
            link_classification="NONE",
            main_bar_classification=role,
            rule_source=rule_source,
            rule_name=self.RULE_NAME_MAIN,
            rule_reference=hook_description or bend_description,
            rule_priority=1,
            structural_code_reference="IS456_ANCHORAGE",
            general_notes_reference=hook_description,
            lookup_path=(
                "structural_detailing_rules",
                "anchorage_rules",
                "HOOK_ANCHORAGE",
                "bend_rules",
            ),
            reinforcement_role=role,
            rule_description=(
                "Main reinforcement uses straight bar profile with standard hook "
                "anchorage at both ends."
            ),
        )

    def _resolve_transverse_rule(
        self,
        role: str,
        hook_rule: Optional[dict[str, Any]],
        bend_rule: Optional[dict[str, Any]],
        rule_source: str,
    ) -> ResolvedShapeCodeRule:
        description = str((hook_rule or {}).get("description", ""))
        is_link = role == "LINK_BAR"
        return ResolvedShapeCodeRule(
            shape_code=role,
            shape_family="TRANSVERSE",
            bend_count=4 if not is_link else 2,
            hook_count=2,
            closed_loop=not is_link,
            open_loop=is_link,
            anchorage_configuration="HOOK_ENDS",
            stirrup_classification="CLOSED" if not is_link else "NONE",
            link_classification="OPEN" if is_link else "NONE",
            main_bar_classification="NONE",
            rule_source=rule_source,
            rule_name=self.RULE_NAME_LINK if is_link else self.RULE_NAME_TRANSVERSE,
            rule_reference=description or "TRANSVERSE_REINFORCEMENT",
            rule_priority=2,
            structural_code_reference="",
            general_notes_reference=description,
            lookup_path=(
                "structural_detailing_rules",
                "anchorage_rules",
                "bend_rules",
                "TRANSVERSE_SHAPE",
            ),
            reinforcement_role=role,
            rule_description=(
                "Closed stirrup profile with hook ends."
                if not is_link
                else "Open link profile with hook ends."
            ),
        )

    def _resolve_side_rule(
        self,
        role: str,
        hook_rule: Optional[dict[str, Any]],
        rule_source: str,
    ) -> ResolvedShapeCodeRule:
        description = str((hook_rule or {}).get("description", ""))
        return ResolvedShapeCodeRule(
            shape_code=role,
            shape_family="SIDE_BAR",
            bend_count=1,
            hook_count=1,
            closed_loop=False,
            open_loop=False,
            anchorage_configuration="SINGLE_HOOK",
            stirrup_classification="NONE",
            link_classification="NONE",
            main_bar_classification="NONE",
            rule_source=rule_source,
            rule_name=self.RULE_NAME_SIDE,
            rule_reference=description or "SIDE_FACE_REINFORCEMENT",
            rule_priority=3,
            structural_code_reference="",
            general_notes_reference=description,
            lookup_path=(
                "structural_detailing_rules",
                "anchorage_rules",
                "SIDE_BAR_SHAPE",
            ),
            reinforcement_role=role,
            rule_description="Side face reinforcement with single hook anchorage.",
        )

    def _resolve_default_rule(
        self,
        role: str,
        hook_rule: Optional[dict[str, Any]],
        bend_rule: Optional[dict[str, Any]],
        rule_source: str,
    ) -> ResolvedShapeCodeRule:
        description = str((hook_rule or {}).get("description", ""))
        return ResolvedShapeCodeRule(
            shape_code=role,
            shape_family="UNKNOWN",
            bend_count=0,
            hook_count=0,
            closed_loop=False,
            open_loop=False,
            anchorage_configuration="UNKNOWN",
            stirrup_classification="NONE",
            link_classification="NONE",
            main_bar_classification="NONE",
            rule_source=rule_source,
            rule_name="DEFAULT_SHAPE",
            rule_reference=description,
            rule_priority=99,
            structural_code_reference="",
            general_notes_reference=description,
            lookup_path=("structural_detailing_rules", "DEFAULT_SHAPE"),
            reinforcement_role=role,
            rule_description="Default straight bar classification.",
        )

    def _collect_bend_rules(self) -> List[dict[str, Any]]:
        structural = self._cache.model.get("structural_detailing_rules", {})
        rules = list(structural.get("bend_rules", []))
        rules.extend(self._cache.model.get("bend_rules", []))
        return rules

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

    def _find_bend_rule(self, rule_type: str) -> Optional[dict[str, Any]]:
        for rule in self._bend_rules:
            if str(rule.get("rule_type", "")).upper() == rule_type.upper():
                return rule
        return self._bend_rules[0] if self._bend_rules else None
