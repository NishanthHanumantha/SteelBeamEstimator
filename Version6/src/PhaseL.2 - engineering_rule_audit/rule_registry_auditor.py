"""Audit the engineering rule registry — discover, map and score every rule."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from engineering_rule_inventory import EngineeringRuleInventory


class RuleRegistryAuditor:
    """Wrap EngineeringRuleInventory and build per-role rule coverage map."""

    def __init__(self, src_root: Path) -> None:
        self._src = src_root
        self._inventory = EngineeringRuleInventory(src_root)

    def audit(self) -> Dict[str, Any]:
        inventory = self._inventory.build()
        rules = inventory.get("rules") or []

        by_role: Dict[str, List[str]] = {}
        for rule in rules:
            for role in (rule.get("roles_referenced") or []):
                by_role.setdefault(role, []).append(rule.get("rule_id", ""))

        dead_candidates = inventory.get("dead_code_candidates") or []

        return {
            "total_rules_discovered": len(rules),
            "rules_by_role": {role: len(ids) for role, ids in sorted(by_role.items())},
            "dead_code_candidates": len(dead_candidates),
            "dead_code_list": [d.get("class_or_function") for d in dead_candidates[:20]],
            "inventory": inventory,
        }
