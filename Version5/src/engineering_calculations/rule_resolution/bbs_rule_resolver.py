"""BBS rule resolver — fabrication policy only, no schedule generation."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.bbs.bbs_types import (
    FABRICATION_MARK_PREFIX,
    RULE_SOURCE_GENERAL_NOTES,
    SCHEDULE_ORDER_ENGINEERING_SIGNATURE,
)
from src.engineering_calculations.rule_resolution.rule_types import ResolvedBbsRule
from src.general_notes.engineering_rule_cache import EngineeringRuleCache


class BbsRuleResolver:
    """Resolve BBS fabrication policy from General Notes / structural cache."""

    RULE_NAME = "BBS_FOUNDATION_POLICY"

    def __init__(self, cache: EngineeringRuleCache) -> None:
        self._cache = cache
        self._detailing_rules = self._collect_detailing_rules()

    def resolve(self, context: dict[str, Any]) -> ResolvedBbsRule:
        bbs_rule = self._find_bbs_rule()
        description = str((bbs_rule or {}).get("description", ""))
        rule_source = str(
            ((bbs_rule or {}).get("provenance") or {}).get("source")
            or RULE_SOURCE_GENERAL_NOTES
        )
        return ResolvedBbsRule(
            fabrication_mark_format=f"{FABRICATION_MARK_PREFIX}{{sequence:03d}}",
            schedule_numbering_policy="SEQUENTIAL_BY_ENGINEERING_ORDER",
            schedule_ordering_policy=SCHEDULE_ORDER_ENGINEERING_SIGNATURE,
            naming_policy="ROLE_SHAPE_DIAMETER",
            rule_source=rule_source,
            rule_name=self.RULE_NAME,
            rule_reference=description or "BBS_FOUNDATION",
            rule_priority=1,
            structural_code_reference="IS456_REINFORCEMENT",
            general_notes_reference=description,
            lookup_path=(
                "structural_detailing_rules",
                "bbs_rules",
                "BBS_FOUNDATION",
            ),
            rule_description=(
                "Fabrication schedule records are generated deterministically "
                "from engineering bar groups without quantity or weight."
            ),
        )

    def _collect_detailing_rules(self) -> List[dict[str, Any]]:
        structural = self._cache.model.get("structural_detailing_rules", {})
        rules = list(structural.get("bbs_rules", []))
        rules.extend(self._cache.model.get("bbs_rules", []))
        return rules

    def _find_bbs_rule(self) -> dict[str, Any] | None:
        for rule in self._detailing_rules:
            if str(rule.get("rule_type", "")).upper() in {"BBS", "BAR_SCHEDULE"}:
                return rule
        for rule in self._detailing_rules:
            description = str(rule.get("description", "")).upper()
            if "BBS" in description or "BAR BENDING SCHEDULE" in description:
                return rule
        return None
