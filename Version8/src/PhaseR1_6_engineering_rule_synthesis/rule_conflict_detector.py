"""
Detect conflicting rules.
MODEL_VERSION: 8.8.0
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple

from engineering_rule_model import EngineeringRule

MODEL_VERSION = "8.8.0"


class RuleConflictDetector:
    def detect(self, rules: List[EngineeringRule]) -> Tuple[List[EngineeringRule], Dict[str, Any]]:
        conflicts: List[Dict[str, Any]] = []
        # Same family duplicate canonical rules
        by_family: Dict[str, List[EngineeringRule]] = defaultdict(list)
        for r in rules:
            by_family[r.rule_family].append(r)
        for fam, items in by_family.items():
            if len(items) > 1:
                conflicts.append({
                    "type": "duplicate_family",
                    "family": fam,
                    "rule_ids": [r.rule_id for r in items],
                    "message": f"Multiple rules in family {fam}",
                })

        # Diameter precedence: Diameter Resolution vs Role Resolution both claiming diameter — informational only if both exist
        fams = {r.rule_family for r in rules}
        if "Diameter Resolution" in fams and "Role Resolution" in fams:
            # not a conflict — dependency handles order; note soft coupling
            pass

        # Cut length vs steel aggregation writing different length precedence
        if "Cut Length" in fams and "Steel Aggregation" in fams:
            conflicts.append({
                "type": "soft_coupling",
                "rule_ids": [
                    next(r.rule_id for r in rules if r.rule_family == "Cut Length"),
                    next(r.rule_id for r in rules if r.rule_family == "Steel Aggregation"),
                ],
                "message": "Cut Length must precede Steel Aggregation; ensure single length source of truth",
                "severity": "info",
            })

        # Attach conflicting_rules soft refs for soft_coupling only as notes, not hard conflicts
        hard = [c for c in conflicts if c.get("type") == "duplicate_family"]
        updated = []
        conflict_map: Dict[str, List[str]] = defaultdict(list)
        for c in hard:
            ids = c.get("rule_ids") or []
            for rid in ids:
                conflict_map[rid].extend([x for x in ids if x != rid])

        for r in rules:
            conf = tuple(sorted(set(conflict_map.get(r.rule_id, []))))
            d = r.to_dict()
            d.pop("model_version", None)
            d["conflicting_rules"] = conf
            updated.append(EngineeringRule(**{k: v for k, v in d.items() if k in EngineeringRule.__dataclass_fields__}))

        return updated, {
            "model_version": MODEL_VERSION,
            "conflict_count": len(conflicts),
            "hard_conflict_count": len(hard),
            "conflicts": conflicts,
            "priority_conflicts": False,
        }
