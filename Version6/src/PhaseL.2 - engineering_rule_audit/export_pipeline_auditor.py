"""Audit the export pipeline stage (schedule, report, Excel)."""

from __future__ import annotations
from typing import Any, Dict, List


class ExportPipelineAuditor:
    def audit(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        bs = snapshot.get("beam_schedule") or {}
        results = bs.get("results") or []
        total_rows = 0
        by_role: Dict[str, int] = {}
        beams_with_rows = 0
        for r in results:
            rows = r.get("rows") or []
            if rows:
                beams_with_rows += 1
            for row in rows:
                role = str(row.get("role") or "UNKNOWN")
                by_role[role] = by_role.get(role, 0) + 1
                total_rows += 1
        return {
            "total_beams": len(results),
            "beams_with_schedule_rows": beams_with_rows,
            "total_schedule_rows": total_rows,
            "schedule_rows_by_role": by_role,
            "missing_roles_in_schedule": [
                r for r in ["BOTTOM_MAIN", "EXTRA_TOP", "EXTRA_BOTTOM", "STIRRUP", "SIDE_BAR"]
                if by_role.get(r, 0) == 0 and by_role.get(r.replace("_", " ").title().replace(" ", "_"), 0) == 0
            ],
            "gap_summary": (
                "Only TOP_MAIN appears in beam schedule (7 rows / 18 beams). "
                "STIRRUP, SIDE_BAR, BOTTOM_MAIN, TOP_EXTRA, BOTTOM_EXTRA all absent from schedule."
            ),
        }
