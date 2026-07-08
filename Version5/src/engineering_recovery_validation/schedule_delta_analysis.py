"""Beam schedule and Excel schedule impact analysis."""

from __future__ import annotations

from typing import Any, List, Set

from src.engineering_recovery_validation.baseline_loader import _is_recovered_bar, _schedule_row_count


class ScheduleDeltaAnalyzer:
    """Compare schedule coverage before and after recovery."""

    def analyze(self, snapshot: dict[str, Any], baseline_snapshot: dict[str, Any]) -> dict[str, Any]:
        pre = baseline_snapshot.get("pre_j1") or {}
        post = baseline_snapshot.get("post_j1") or {}
        recovery_index = snapshot.get("recovery_index") or {}
        recovered_bar_ids = set(recovery_index.get("recovered_bar_ids") or [])

        bars = snapshot.get("bars") or []
        bbs_records = snapshot.get("bbs_records") or []
        beam_schedules = snapshot.get("beam_schedules") or []
        excel_statistics = snapshot.get("excel_statistics") or {}
        excel_validation = snapshot.get("excel_validation") or {}

        recovered_bbs = [
            item
            for item in bbs_records
            if str(item.get("bar_id") or "") in recovered_bar_ids
            or recovered_bar_ids.intersection(set(item.get("member_bar_ids") or []))
        ]
        baseline_bbs = [
            item
            for item in bbs_records
            if str(item.get("bar_id") or "") not in recovered_bar_ids
            and not recovered_bar_ids.intersection(set(item.get("member_bar_ids") or []))
        ]

        recovered_beams = sorted(
            {
                str(bar.get("beam_id"))
                for bar in bars
                if _is_recovered_bar(bar, recovered_bar_ids) and bar.get("beam_id")
            }
        )
        schedule_beams = sorted(
            {
                str(item.get("beam_id") or item.get("beam_mark") or "")
                for item in beam_schedules
                if item.get("beam_id") or item.get("beam_mark")
            }
        )

        excel_rows_written = int(excel_statistics.get("rows_written") or 0)
        excel_export_rows = self._count_excel_export_rows(excel_validation)

        return {
            "schedule_rows": {
                "before": pre.get("beam_schedule_rows", 0),
                "after": post.get("beam_schedule_rows", 0),
                "delta": post.get("beam_schedule_rows", 0) - pre.get("beam_schedule_rows", 0),
            },
            "bbs_rows": {
                "before": len(baseline_bbs),
                "after": len(bbs_records),
                "delta": len(recovered_bbs),
                "recovered_bbs_entries": len(recovered_bbs),
            },
            "excel_rows": {
                "before": pre.get("excel_rows", excel_rows_written),
                "after": post.get("excel_rows", excel_rows_written),
                "delta": post.get("excel_rows", excel_rows_written) - pre.get("excel_rows", excel_rows_written),
                "rows_written": excel_rows_written,
                "validation_row_count": excel_export_rows,
            },
            "recovered_schedule_beams": recovered_beams,
            "engineering_schedule_coverage": {
                "beams_in_schedule": len(schedule_beams),
                "beams_with_recovered_bars": len(recovered_beams),
                "schedule_beam_ids": schedule_beams,
            },
            "new_bbs_entries": [item.get("bbs_id") for item in recovered_bbs],
            "recovered_rows": len(recovered_bbs),
        }

    @staticmethod
    def _count_excel_export_rows(excel_validation: dict[str, Any]) -> int:
        rows = excel_validation.get("rows") or excel_validation.get("exported_rows") or []
        if isinstance(rows, list):
            return len(rows)
        summary = excel_validation.get("summary") or {}
        return int(summary.get("row_count") or summary.get("rows_written") or 0)
