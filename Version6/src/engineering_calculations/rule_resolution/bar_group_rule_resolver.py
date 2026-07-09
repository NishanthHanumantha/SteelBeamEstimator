"""Bar group rule resolver — grouping policy only, no aggregation or IDs."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.bar_group.bar_group_types import (
    GROUPING_STRATEGY_ENGINEERING_SIGNATURE,
    RULE_SOURCE_GENERAL_NOTES,
)
from src.engineering_calculations.rule_resolution.rule_types import ResolvedBarGroupRule
from src.general_notes.engineering_rule_cache import EngineeringRuleCache


class BarGroupRuleResolver:
    """Resolve bar group aggregation policy from General Notes / structural cache."""

    RULE_NAME = "ENGINEERING_SIGNATURE_GROUPING"

    def __init__(self, cache: EngineeringRuleCache) -> None:
        self._cache = cache
        self._detailing_rules = self._collect_detailing_rules()

    def resolve(
        self,
        context: dict[str, Any],
    ) -> ResolvedBarGroupRule:
        group_rule = self._find_group_rule()
        description = str((group_rule or {}).get("description", ""))
        rule_source = str(
            ((group_rule or {}).get("provenance") or {}).get("source")
            or RULE_SOURCE_GENERAL_NOTES
        )
        return ResolvedBarGroupRule(
            grouping_strategy=GROUPING_STRATEGY_ENGINEERING_SIGNATURE,
            group_by_identity=True,
            group_by_geometry=True,
            group_by_shape=True,
            group_by_cut_length=True,
            rule_source=rule_source,
            rule_name=self.RULE_NAME,
            rule_reference=description or "ENGINEERING_BAR_GROUP_AGGREGATION",
            rule_priority=1,
            structural_code_reference="IS456_REINFORCEMENT",
            general_notes_reference=description,
            lookup_path=(
                "structural_detailing_rules",
                "group_rules",
                "ENGINEERING_SIGNATURE",
            ),
            rule_description=(
                "Engineering-identical bars are combined into reusable "
                "engineering group objects using immutable engineering signatures."
            ),
        )

    def _collect_detailing_rules(self) -> List[dict[str, Any]]:
        structural = self._cache.model.get("structural_detailing_rules", {})
        rules = list(structural.get("group_rules", []))
        rules.extend(self._cache.model.get("group_rules", []))
        return rules

    def _find_group_rule(self) -> dict[str, Any] | None:
        for rule in self._detailing_rules:
            if str(rule.get("rule_type", "")).upper() == "BAR_GROUP":
                return rule
        for rule in self._detailing_rules:
            description = str(rule.get("description", "")).upper()
            if "BAR GROUP" in description or "AGGREGATION" in description:
                return rule
        return None
