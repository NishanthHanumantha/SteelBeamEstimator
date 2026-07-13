"""Compare every estimator reinforcement to a Version6 pipeline execution path."""

from __future__ import annotations

from typing import Any, Dict, List

ESTIMATOR_ABSENCE_REASONS = {
    "TOP_MAIN": "EXPORT_STOP — partial schedule rows only",
    "BOTTOM_MAIN": "GEOMETRY_STOP — 0 engineering objects created",
    "TOP_EXTRA": "GEOMETRY_STOP — 0 engineering objects created",
    "BOTTOM_EXTRA": "GEOMETRY_STOP — 0 engineering objects created",
    "STIRRUP": "QUANTITY_STOP — steel weight DEFERRED",
    "SIDE_FACE": "EXPORT_STOP — excluded from schedule builder",
    "SPACER_BAR": "GEOMETRY_STOP — spec-driven creation not wired",
    "CHAIR_BAR": "PARSER_STOP — not implemented",
    "UNKNOWN": "UNKNOWN — no trace available",
}


class EstimatorTraceComparator:
    """For every estimator reinforcement, locate matching Version6 execution path."""

    def compare(
        self,
        role_audit: List[Dict[str, Any]],
        status_classifications: List[Dict[str, Any]],
        snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        l1_role_gap = snapshot.get("l1_role_gap") or {}
        role_gap_rows = l1_role_gap.get("rows") or []
        status_by_role = {s["role"]: s for s in status_classifications}
        audit_by_role = {r["role"]: r for r in role_audit}

        traces: List[Dict[str, Any]] = []
        for gap_row in role_gap_rows:
            role = str(gap_row.get("role") or "")
            est_bars = int(gap_row.get("estimator_bar_count") or 0)
            est_weight = float(gap_row.get("estimator_weight_kg") or 0.0)
            status = status_by_role.get(role, {})
            audit = audit_by_role.get(role, {})

            v6_bars = int(audit.get("bar_count") or 0)
            v6_sched = int(audit.get("schedule_row_count") or 0)
            matched = v6_sched > 0 and est_bars > 0

            absence_reason = None
            if not matched:
                absence_reason = ESTIMATOR_ABSENCE_REASONS.get(role, "UNKNOWN")

            traces.append({
                "role": role,
                "estimator_bar_count": est_bars,
                "estimator_weight_kg": est_weight,
                "v6_bar_count": v6_bars,
                "v6_schedule_rows": v6_sched,
                "matched": matched,
                "match_quality": "FULL" if (matched and v6_sched >= est_bars) else (
                    "PARTIAL" if matched else "NONE"
                ),
                "absence_reason": absence_reason,
                "implementation_status": status.get("implementation_status", "UNKNOWN"),
                "break_stage": status.get("break_stage"),
                "execution_stop_type": ESTIMATOR_ABSENCE_REASONS.get(role),
            })

        total = len(traces)
        matched_count = sum(1 for t in traces if t["matched"])
        return {
            "total_estimator_roles": total,
            "matched_roles": matched_count,
            "unmatched_roles": total - matched_count,
            "match_percent": round(100 * matched_count / max(total, 1), 2),
            "traces": traces,
        }
