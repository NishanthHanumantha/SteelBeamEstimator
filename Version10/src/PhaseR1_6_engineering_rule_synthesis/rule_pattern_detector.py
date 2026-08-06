"""
Consolidate recurring issues into canonical rule patterns.
MODEL_VERSION: 8.8.0
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple

from rule_family_classifier import RuleFamilyClassifier

MODEL_VERSION = "8.8.0"


class RulePatternDetector:
    def __init__(self):
        self._clf = RuleFamilyClassifier()

    def detect(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for issue in issues:
            family = self._clf.classify(issue.get("category") or "", issue.get("subcategory") or "")
            key = self._clf.pattern_key(family, issue.get("subcategory") or "")
            groups[key].append(issue)

        patterns = []
        for key, items in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            family = key.split("::")[0]
            patterns.append({
                "pattern_id": key,
                "rule_family": family,
                "issue_count": len(items),
                "finding_count": sum(int(i.get("frequency") or 0) for i in items),
                "issue_ids": [i.get("issue_id") for i in items],
                "consolidated": len(items) > 1 or sum(int(i.get("frequency") or 0) for i in items) > 1,
                "message": (
                    f"{sum(int(i.get('frequency') or 0) for i in items)} findings across "
                    f"{len(items)} issues → one {family} rule"
                ),
            })
        return {
            "model_version": MODEL_VERSION,
            "pattern_count": len(patterns),
            "patterns": patterns,
            "groups": {k: [i.get("issue_id") for i in v] for k, v in groups.items()},
        }
