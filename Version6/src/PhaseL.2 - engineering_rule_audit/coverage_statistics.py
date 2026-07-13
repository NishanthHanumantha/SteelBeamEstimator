"""Compute engineering rule audit coverage statistics."""

from __future__ import annotations

from typing import Any, Dict, List


class CoverageStatistics:
    """Compute coverage percentages across all audit dimensions."""

    def build(
        self,
        status_classifications: List[Dict[str, Any]],
        execution_paths: List[Dict[str, Any]],
        role_audit: List[Dict[str, Any]],
        rule_registry: Dict[str, Any],
        pipeline_trace: Dict[str, Any],
        estimator_trace: Dict[str, Any],
    ) -> Dict[str, Any]:
        total = len(status_classifications)
        if not total:
            return {}

        implemented_pct = self._pct(
            [s for s in status_classifications if s.get("implementation_status") == "IMPLEMENTED"], total
        )
        executed_pct = self._pct(
            [s for s in status_classifications if s.get("implementation_status") in (
                "IMPLEMENTED", "PARTIALLY_EXECUTED", "EXECUTED_NOT_EXPORTED"
            )], total
        )
        reachable_pct = self._pct(
            [s for s in status_classifications if s.get("reachable")], total
        )
        exported_pct = self._pct(
            [r for r in role_audit if r.get("exported")], len(role_audit)
        )
        dead_code_pct = self._pct(
            [s for s in status_classifications if s.get("dead_code")], total
        )
        not_implemented = [
            s for s in status_classifications if s.get("implementation_status") == "NOT_IMPLEMENTED"
        ]
        unused_rules_pct = self._pct(not_implemented, total)
        partial_exec = [
            s for s in status_classifications if s.get("implementation_status") in (
                "PARTIALLY_EXECUTED", "PARTIALLY_IMPLEMENTED", "IMPLEMENTED_NOT_EXECUTED",
                "EXECUTED_NOT_EXPORTED",
            )
        ]
        pipeline_completion_pct = self._pct(
            [r for r in role_audit if r.get("exported")], len(role_audit)
        )
        est_coverage = estimator_trace.get("match_percent", 0.0)

        stages = pipeline_trace.get("pipeline_stages") or []
        stage_completion = {
            stage: self._pct(
                [r for r in role_audit if self._stage_pass(r, stage)], len(role_audit)
            )
            for stage in stages[:8]
        }

        return {
            "implemented_percent": implemented_pct,
            "executed_percent": executed_pct,
            "reachable_percent": reachable_pct,
            "exported_percent": exported_pct,
            "estimator_coverage_percent": est_coverage,
            "dead_code_percent": dead_code_pct,
            "unused_rule_percent": unused_rules_pct,
            "pipeline_completion_percent": pipeline_completion_pct,
            "total_roles_audited": total,
            "fully_implemented": sum(1 for s in status_classifications if s.get("implementation_status") == "IMPLEMENTED"),
            "partially_executed": len(partial_exec),
            "not_implemented": len(not_implemented),
            "dead_code_count": sum(1 for s in status_classifications if s.get("dead_code")),
            "stage_completion_percent": stage_completion,
            "total_engineering_rules_discovered": rule_registry.get("total_rules_discovered", 0),
            "dead_code_rule_candidates": rule_registry.get("dead_code_candidates", 0),
        }

    @staticmethod
    def _pct(subset: List, total: int) -> float:
        return round(100 * len(subset) / max(total, 1), 2)

    @staticmethod
    def _stage_pass(role_row: Dict[str, Any], stage: str) -> bool:
        if stage == "DRAWING_DETECTION":
            return bool(role_row.get("detected"))
        if stage == "PARSING":
            return bool(role_row.get("parsed"))
        if stage in ("GEOMETRY_CREATION", "ENGINEERING_OBJECT_CREATION"):
            return bool(role_row.get("geometry"))
        if stage == "OWNERSHIP_ASSIGNMENT":
            return bool(role_row.get("ownership"))
        if stage == "SPECIFICATION_NORMALIZATION":
            return bool(role_row.get("context"))
        if stage == "CALCULATION_CONTEXT":
            return bool(role_row.get("context"))
        if stage == "RULE_SELECTION":
            return bool(role_row.get("rule_exists"))
        if stage == "RULE_EXECUTION":
            return bool(role_row.get("rule_executed"))
        return False
