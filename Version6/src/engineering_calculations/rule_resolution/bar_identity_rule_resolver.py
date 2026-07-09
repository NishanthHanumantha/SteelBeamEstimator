"""Bar identity rule resolver — grouping rules only, no identity generation."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.bar_identity.bar_identity_types import (
    EQUIVALENCE_ATTRIBUTE_KEYS,
    GROUPING_STRATEGY_ENGINEERING_EQUIVALENCE,
    RULE_SOURCE_GENERAL_NOTES,
)
from src.engineering_calculations.rule_resolution.rule_types import ResolvedBarIdentityRule
from src.general_notes.engineering_rule_cache import EngineeringRuleCache


class BarIdentityRuleResolver:
    """Resolve bar grouping rules from General Notes / structural cache."""

    RULE_NAME = "ENGINEERING_EQUIVALENCE_GROUPING"

    def __init__(self, cache: EngineeringRuleCache) -> None:
        self._cache = cache
        self._detailing_rules = self._collect_detailing_rules()

    def resolve(
        self,
        bar: dict[str, Any],
        context: dict[str, Any],
    ) -> ResolvedBarIdentityRule:
        identity_rule = self._find_identity_rule()
        description = str((identity_rule or {}).get("description", ""))
        rule_source = str(
            ((identity_rule or {}).get("provenance") or {}).get("source")
            or RULE_SOURCE_GENERAL_NOTES
        )
        role = str(bar.get("role") or "UNKNOWN").upper()
        return ResolvedBarIdentityRule(
            grouping_strategy=GROUPING_STRATEGY_ENGINEERING_EQUIVALENCE,
            equivalence_attributes=tuple(sorted(EQUIVALENCE_ATTRIBUTE_KEYS)),
            include_support_configuration=True,
            include_geometry_signature=True,
            rule_source=rule_source,
            rule_name=self.RULE_NAME,
            rule_reference=description or "ENGINEERING_BAR_EQUIVALENCE",
            rule_priority=1,
            structural_code_reference="IS456_REINFORCEMENT",
            general_notes_reference=description,
            lookup_path=(
                "structural_detailing_rules",
                "identity_rules",
                "ENGINEERING_EQUIVALENCE",
            ),
            reinforcement_role=role,
            rule_description=(
                "Bars with identical engineering characteristics are grouped "
                "before individual engineering identities are assigned."
            ),
        )

    def _collect_detailing_rules(self) -> List[dict[str, Any]]:
        structural = self._cache.model.get("structural_detailing_rules", {})
        rules = list(structural.get("identity_rules", []))
        rules.extend(self._cache.model.get("identity_rules", []))
        return rules

    def _find_identity_rule(self) -> dict[str, Any] | None:
        for rule in self._detailing_rules:
            if str(rule.get("rule_type", "")).upper() == "BAR_IDENTITY":
                return rule
        for rule in self._detailing_rules:
            description = str(rule.get("description", "")).upper()
            if "IDENTITY" in description or "EQUIVALENCE" in description:
                return rule
        return None
