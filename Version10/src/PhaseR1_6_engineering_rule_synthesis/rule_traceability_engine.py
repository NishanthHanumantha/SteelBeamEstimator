"""
Issue → Rule → Future Correction traceability.
MODEL_VERSION: 8.8.0
"""
from __future__ import annotations

from typing import Any, Dict, List

from engineering_rule_model import EngineeringRule

MODEL_VERSION = "8.8.0"


class RuleTraceabilityEngine:
    def build(
        self,
        rules: List[EngineeringRule],
        issues: List[Dict[str, Any]],
        backlog: Dict[str, Any],
    ) -> Dict[str, Any]:
        issue_to_rule: Dict[str, str] = {}
        for r in rules:
            for iid in r.originating_issues:
                issue_to_rule[iid] = r.rule_id

        rows = []
        for issue in issues:
            iid = issue.get("issue_id")
            rid = issue_to_rule.get(iid)
            rule = next((r for r in rules if r.rule_id == rid), None)
            rows.append({
                "issue_id": iid,
                "finding_ids": issue.get("finding_ids") or [],
                "rule_id": rid,
                "rule_family": rule.rule_family if rule else None,
                "recommended_phase": issue.get("recommended_phase"),
                "implementation_phase": rule.implementation_phase if rule else None,
                "evidence_count": len(issue.get("supporting_evidence") or []),
                "future_correction": f"CORRECT::{rid}" if rid else None,
                "future_benchmark": "R.1.4 re-benchmark after correction",
            })

        unmapped = [r["issue_id"] for r in rows if not r["rule_id"]]
        return {
            "model_version": MODEL_VERSION,
            "mapped_issues": len(rows) - len(unmapped),
            "unmapped_issues": unmapped,
            "complete": len(unmapped) == 0,
            "rows": rows,
            "backlog_ref": {
                "item_count": backlog.get("item_count"),
                "cumulative_expected_gain_pct": backlog.get("cumulative_expected_gain_pct"),
            },
        }
