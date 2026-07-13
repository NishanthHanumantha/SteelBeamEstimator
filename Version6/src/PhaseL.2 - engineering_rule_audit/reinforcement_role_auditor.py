"""Per-role audit table: detected, parsed, owned, rule exists, executed, etc."""

from __future__ import annotations

from typing import Any, Dict, List

AUDIT_COLUMNS = (
    "detected", "parsed", "geometry", "ownership", "context",
    "rule_exists", "rule_executed", "quantity", "exported", "estimator_match",
)


class ReinforcementRoleAuditor:
    """Build per-role 10-column audit table."""

    def audit(
        self,
        pipeline_trace: Dict[str, Any],
        breaks: List[Dict[str, Any]],
        status_classifications: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        break_by_role = {b["role"]: b for b in breaks}
        status_by_role = {s["role"]: s for s in status_classifications}
        per_role = pipeline_trace.get("per_role_traces") or []
        rows: List[Dict[str, Any]] = []

        for trace in per_role:
            role = str(trace.get("role") or "")
            brk = break_by_role.get(role, {})
            status = status_by_role.get(role, {})
            stages = {s["stage"]: s for s in (trace.get("stages") or [])}

            def _stage_yes(name: str) -> bool:
                s = stages.get(name, {})
                return s.get("result") in ("YES", "PARTIAL", "INFERRED", "N/A", "CONDITIONAL", "PARTIAL")

            obj_count = trace.get("engineering_object_count", 0)
            sw_count = trace.get("steel_weight_count", 0)
            sw_calc = trace.get("steel_weight_calculated", 0)
            sw_defer = trace.get("steel_weight_deferred", 0)
            sched = trace.get("schedule_row_count", 0)

            rows.append({
                "role": role,
                "detected": _stage_yes("DRAWING_DETECTION"),
                "parsed": _stage_yes("PARSING"),
                "geometry": obj_count > 0,
                "ownership": obj_count > 0,
                "context": _stage_yes("CALCULATION_CONTEXT") and obj_count > 0,
                "rule_exists": status.get("reachable", True) or status.get("rule_module") is not None,
                "rule_executed": (sw_count > 0 and sw_calc > 0) or sw_defer > 0,
                "quantity": sw_calc > 0,
                "exported": sched > 0,
                "estimator_match": sched > 0,
                "engineering_object_count": obj_count,
                "bar_count": trace.get("bar_count", 0),
                "steel_weight_calculated": sw_calc,
                "steel_weight_deferred": sw_defer,
                "schedule_row_count": sched,
                "implementation_status": status.get("implementation_status", "UNKNOWN"),
                "break_category": brk.get("break_category", "UNKNOWN"),
                "break_stage": brk.get("break_stage"),
                "rule_module": status.get("rule_module"),
                "rule_class": status.get("rule_class"),
            })
        return rows
