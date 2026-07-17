"""Compute pipeline health and integrity scores."""
from __future__ import annotations
from typing import Any, Dict

from .validation_models import RuleResult


class ValidationStatistics:

    def compute_scores(
        self,
        rules: Dict[str, RuleResult],
        coverage: Dict[str, Any],
        gate_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        rule_list = [r for k, r in rules.items() if not k.startswith("_")]
        pass_count = sum(1 for r in rule_list if r.status == "PASS")
        warn_count = sum(1 for r in rule_list if r.status == "WARNING")
        error_count = sum(1 for r in rule_list if r.status == "ERROR")
        total_rules = len(rule_list)

        integrity_score = (
            round(100.0 * pass_count / total_rules, 2) if total_rules else 0.0
        )

        coverage_factor = coverage.get("coverage_pct", 0) / 100.0
        propagation_factor = coverage.get("propagation_pct", 0) / 100.0
        orphan_penalty = min(
            1.0,
            coverage.get("orphan_reinforcement_groups", 0) * 0.1
            + len(coverage.get("orphan_engineering_beams", [])) * 0.1,
        )
        dup_penalty = min(1.0, len(coverage.get("duplicate_beams", [])) * 0.2)
        gate_factor = 1.0 if gate_result.get("status") == "PASS" else 0.7

        pipeline_health = round(
            100.0
            * (
                0.35 * coverage_factor
                + 0.35 * propagation_factor
                + 0.15 * gate_factor
                + 0.15 * (1.0 - orphan_penalty - dup_penalty)
            ),
            2,
        )

        return {
            "integrity_score": integrity_score,
            "pipeline_health_score": max(0.0, pipeline_health),
            "rule_summary": {
                "total": total_rules,
                "passed": pass_count,
                "warnings": warn_count,
                "errors": error_count,
            },
            "coverage_pct": coverage.get("coverage_pct", 0),
            "propagation_pct": coverage.get("propagation_pct", 0),
            "average_bars_per_beam": coverage.get("average_bars_per_beam", 0),
            "total_engineering_bars": coverage.get("total_engineering_bars", 0),
            "role_distribution": coverage.get("role_distribution", {}),
            "diameter_distribution": coverage.get("diameter_distribution", {}),
        }
