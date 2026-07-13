"""Analyze Rule exists / called / completed / output / exported."""

from __future__ import annotations

from typing import Any, Dict, List


class ExecutionPathAnalyzer:
    """Build execution path record for every engineering capability."""

    def analyze(
        self,
        status_classifications: List[Dict[str, Any]],
        rule_inventory: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        rule_lookup: Dict[str, Any] = {}
        for rule in (rule_inventory.get("rules") or []):
            for role in (rule.get("roles_referenced") or []):
                rule_lookup.setdefault(role, []).append(rule)

        results: List[Dict[str, Any]] = []
        for sc in status_classifications:
            role = str(sc.get("role") or "")
            rules_for_role = rule_lookup.get(role, [])
            status = str(sc.get("implementation_status") or "")

            rule_exists = bool(sc.get("rule_module")) or len(rules_for_role) > 0
            rule_called = status not in ("NOT_IMPLEMENTED", "PARSER_ONLY")
            rule_completed = status in (
                "IMPLEMENTED", "PARTIALLY_EXECUTED", "EXECUTED_NOT_EXPORTED",
            )
            output_produced = bool(sc.get("steel_weight_calculated") or sc.get("execution_count"))
            output_exported = bool(sc.get("schedule_row_count"))

            results.append({
                "role": role,
                "rule_exists": rule_exists,
                "rule_exists_detail": sc.get("rule_module") or (
                    rules_for_role[0]["module_path"] if rules_for_role else "Not found"
                ),
                "rule_called": rule_called,
                "rule_called_detail": self._call_detail(status, sc),
                "rule_completed": rule_completed,
                "rule_completed_detail": self._completion_detail(status, sc),
                "output_produced": output_produced,
                "output_produced_detail": self._output_detail(sc),
                "output_exported": output_exported,
                "output_exported_detail": f"Schedule rows: {sc.get('schedule_row_count', 0)}",
                "implementation_status": status,
                "execution_stop": sc.get("break_stage"),
            })
        return results

    @staticmethod
    def _call_detail(status: str, sc: Dict[str, Any]) -> str:
        if status == "NOT_IMPLEMENTED":
            return "Rule not implemented — never called"
        if status in ("GEOMETRY_ONLY", "CONTEXT_ONLY", "PARSER_ONLY"):
            return "Rule not reached — execution stopped before rule selection"
        if status == "IMPLEMENTED_NOT_EXECUTED":
            return f"Rule implemented in {sc.get('rule_module')} but execution path disconnected — no bars reach this rule"
        if status == "PARTIALLY_IMPLEMENTED":
            return "Rule partially implemented — code path exists but not connected for all bars"
        return f"Rule called — execution count: {sc.get('execution_count') or 'partial'}"

    @staticmethod
    def _completion_detail(status: str, sc: Dict[str, Any]) -> str:
        if status in ("NOT_IMPLEMENTED", "PARSER_ONLY", "GEOMETRY_ONLY"):
            return "Did not complete — never started"
        if status == "IMPLEMENTED_NOT_EXECUTED":
            return "Did not complete — execution path disconnected"
        if status == "EXECUTED_NOT_EXPORTED":
            sw_defer = sc.get("steel_weight_deferred", 0)
            sw_calc = sc.get("steel_weight_calculated", 0)
            if sw_defer > 0:
                return f"Completed partially — {sw_calc} calculated, {sw_defer} deferred (missing prerequisites)"
            return f"Calculated {sw_calc} entries but not exported to schedule"
        if status == "PARTIALLY_EXECUTED":
            return f"Partial completion — {sc.get('schedule_row_count', 0)} exported of estimated total"
        return "Completed"

    @staticmethod
    def _output_detail(sc: Dict[str, Any]) -> str:
        sw_calc = sc.get("steel_weight_calculated") or 0
        sw_defer = sc.get("steel_weight_deferred") or 0
        count = sc.get("execution_count")
        if sw_calc:
            return f"Steel weight calculated: {sw_calc} entries"
        if sw_defer:
            return f"Steel weight DEFERRED: {sw_defer} entries (dependency missing)"
        if count:
            return f"Execution count: {count}"
        return "No output produced"
