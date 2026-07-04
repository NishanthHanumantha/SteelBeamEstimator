"""Lap splice rule resolver — rule selection only, no mathematics."""

from __future__ import annotations

import re
from typing import Any, List, Optional

from src.engineering_calculations.lap_length_types import (
    COMPRESSION_POSITION,
    RULE_SOURCE_GENERAL_NOTES,
    RULE_SOURCE_STRUCTURAL_CODE,
    TENSION_POSITION,
)
from src.engineering_calculations.rule_resolution.rule_types import ResolvedLapRule
from src.general_notes.engineering_rule_cache import EngineeringRuleCache
from src.general_notes.engineering_value import engineering_value_numeric


class LapRuleResolver:
    """Resolve applicable lap splice rules from General Notes / structural code cache."""

    RULE_NAME_TABLE_1 = "LAP_SPLICE_TABLE_1"
    RULE_NAME_MINIMUM_LAP = "MINIMUM_LAP_LENGTH"
    RULE_NAME_OPTIONAL_INCREASE = "LAP_SPLICE_30_PERCENT_INCREASE"

    def __init__(self, cache: EngineeringRuleCache) -> None:
        self._cache = cache
        self._rules = self._collect_fabrication_rules()

    def resolve(
        self,
        bar: dict[str, Any],
        context: dict[str, Any],
    ) -> ResolvedLapRule:
        position = self._resolve_reinforcement_position(bar, context)
        minimum_lap_mm = self._resolve_minimum_lap_mm()
        table_rule = self._find_rule("AS PER TABLE-1")
        increase_rule = self._find_rule("INCREASED BY 30%")

        if table_rule:
            rule_source = str(
                (table_rule.get("provenance") or {}).get("source") or RULE_SOURCE_GENERAL_NOTES
            )
            description = str(table_rule.get("description", ""))
            lookup_path = [
                "structural_detailing_rules",
                "fabrication_rules",
                "LAP_SPLICE",
                "TABLE-1",
            ]
            rule_name = self.RULE_NAME_TABLE_1
            rule_reference = description
            general_notes_reference = description
            structural_code_reference = ""
            rule_priority = 1
        else:
            rule_source = RULE_SOURCE_STRUCTURAL_CODE
            description = "Default structural code lap splice equals development length."
            lookup_path = [
                "engineering_constants",
                "minimum_lap_mm",
            ]
            rule_name = self.RULE_NAME_MINIMUM_LAP
            rule_reference = "engineering_constants.minimum_lap_mm"
            general_notes_reference = ""
            structural_code_reference = "engineering_constants.minimum_lap_mm"
            rule_priority = 2

        if increase_rule:
            lookup_path = list(lookup_path) + ["OPTIONAL_30_PERCENT_INCREASE"]

        return ResolvedLapRule(
            lap_factor=1.0,
            minimum_lap_mm=minimum_lap_mm,
            rule_source=rule_source,
            rule_name=rule_name,
            rule_reference=rule_reference,
            rule_priority=rule_priority,
            structural_code_reference=structural_code_reference,
            general_notes_reference=general_notes_reference,
            lookup_path=tuple(lookup_path),
            reinforcement_position=position,
            rule_description=description,
        )

    def _collect_fabrication_rules(self) -> List[dict[str, Any]]:
        structural = self._cache.model.get("structural_detailing_rules", {})
        rules = list(structural.get("fabrication_rules", []))
        rules.extend(self._cache.model.get("fabrication_rules", []))
        return rules

    def _find_rule(self, needle: str) -> Optional[dict[str, Any]]:
        needle_upper = needle.upper()
        for rule in self._rules:
            description = str(rule.get("description", "")).upper()
            if needle_upper in description:
                return rule
        return None

    def _resolve_minimum_lap_mm(self) -> int:
        for rule in self._rules:
            description = str(rule.get("description", "")).upper()
            if "LAP LENGTH LESS THAN" in description:
                match = re.search(r"(\d+)\s*MM", description)
                if match:
                    return int(match.group(1))

        constants = self._cache.model.get("engineering_constants", {})
        minimum = engineering_value_numeric(constants.get("minimum_lap_mm"))
        if minimum is not None:
            return int(minimum)

        minimum_obj = constants.get("minimum_lap") or {}
        nested = engineering_value_numeric(minimum_obj.get("value"))
        if nested is not None:
            return int(nested)

        return 300

    @staticmethod
    def _resolve_reinforcement_position(
        bar: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        role = str(bar.get("role") or "").upper()
        compression_roles = {"COMPRESSION_BAR", "COMPRESSION", "STIRRUP", "LINK_BAR"}
        if role in compression_roles:
            return COMPRESSION_POSITION

        position = str(bar.get("position") or context.get("position") or "").upper()
        if "COMPRESSION" in position:
            return COMPRESSION_POSITION
        return TENSION_POSITION
