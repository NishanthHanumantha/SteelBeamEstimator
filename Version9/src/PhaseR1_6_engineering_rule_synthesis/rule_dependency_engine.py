"""
Rule dependency graph — no circular dependencies.
MODEL_VERSION: 8.8.0
"""
from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from engineering_rule_model import EngineeringRule
from rule_synthesis_engine import template_for

MODEL_VERSION = "8.8.0"


class RuleDependencyEngine:
    def apply(self, rules: List[EngineeringRule]) -> Tuple[List[EngineeringRule], Dict[str, Any]]:
        by_family = {r.rule_family: r.rule_id for r in rules}
        updated: List[EngineeringRule] = []
        edges: List[Dict[str, str]] = []

        for rule in rules:
            tpl = template_for(rule.rule_family)
            dep_families = tuple(tpl.get("deps_families") or ())  # type: ignore
            dep_ids = []
            for fam in dep_families:
                if fam in by_family and by_family[fam] != rule.rule_id:
                    dep_ids.append(by_family[fam])
                    edges.append({
                        "from": rule.rule_id,
                        "to": by_family[fam],
                        "from_family": rule.rule_family,
                        "to_family": fam,
                    })
            updated.append(self._with_deps(rule, tuple(dep_ids)))

        cycles = self._find_cycles(updated)
        return updated, {
            "model_version": MODEL_VERSION,
            "edge_count": len(edges),
            "edges": edges,
            "nodes": [{"rule_id": r.rule_id, "family": r.rule_family, "deps": list(r.dependencies)} for r in updated],
            "circular_dependencies": cycles,
            "acyclic": len(cycles) == 0,
        }

    @staticmethod
    def _with_deps(rule: EngineeringRule, deps: Tuple[str, ...]) -> EngineeringRule:
        d = rule.to_dict()
        d.pop("model_version", None)
        d["dependencies"] = deps
        return EngineeringRule(**{k: v for k, v in d.items() if k in EngineeringRule.__dataclass_fields__})

    def _find_cycles(self, rules: List[EngineeringRule]) -> List[List[str]]:
        graph = {r.rule_id: list(r.dependencies) for r in rules}
        cycles: List[List[str]] = []
        visiting: Set[str] = set()
        visited: Set[str] = set()
        stack: List[str] = []

        def dfs(node: str) -> None:
            if node in visited:
                return
            if node in visiting:
                if node in stack:
                    cycles.append(stack[stack.index(node):] + [node])
                return
            visiting.add(node)
            stack.append(node)
            for nxt in graph.get(node, []):
                dfs(nxt)
            stack.pop()
            visiting.discard(node)
            visited.add(node)

        for n in graph:
            dfs(n)
        return cycles
