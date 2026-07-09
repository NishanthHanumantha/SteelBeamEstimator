"""Per-beam engineering completeness analysis."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Set

from src.engineering_analysis.coverage_collector import REINFORCEMENT_CATEGORIES, category_for_role, round_pct


class BeamCoverageAnalyzer:
    """Generate one completeness report per beam."""

    STAGE_KEYS = (
        "geometry",
        "specification",
        "groups",
        "bars",
        "ready",
        "calculated",
        "bbs",
        "excel",
    )

    def analyze(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        beam_ids = snapshot.get("beam_ids") or []
        bars = snapshot.get("bars") or []
        groups = snapshot.get("groups") or []
        contexts = snapshot.get("contexts") or []
        bbs_records = snapshot.get("bbs_records") or []
        beam_schedules = snapshot.get("beam_schedules") or []
        engineering_reports = snapshot.get("engineering_reports") or []
        calculated_bar_ids = set(snapshot.get("calculated_bar_ids") or [])
        ready_bar_ids = set(snapshot.get("ready_bar_ids") or [])
        excel_beams = snapshot.get("excel_beams") or {}

        bars_by_beam = self._index_by_beam(bars, "beam_id")
        groups_by_beam = self._index_by_beam(groups, "beam_id")
        contexts_by_beam = self._index_by_beam(contexts, "beam_id")
        bbs_by_beam = self._index_by_beam(bbs_records, "beam_id")
        schedules_by_beam = {
            str(item.get("beam_mark") or item.get("beam_id")): item for item in beam_schedules
        }
        reports_by_beam = {
            str(item.get("beam_mark") or item.get("beam_id")): item for item in engineering_reports
        }

        reports: List[dict[str, Any]] = []
        for beam_id in beam_ids:
            beam_bars = bars_by_beam.get(beam_id, [])
            beam_groups = groups_by_beam.get(beam_id, [])
            beam_contexts = contexts_by_beam.get(beam_id, [])
            schedule = schedules_by_beam.get(beam_id, {})
            report = reports_by_beam.get(beam_id, {})
            excel_block = excel_beams.get(beam_id)

            stage_status = {
                "geometry": self._stage_flag(beam_contexts or beam_bars, "geometry"),
                "specification": self._stage_flag(beam_bars, "specification"),
                "groups": len(beam_groups) > 0,
                "bars": len(beam_bars) > 0,
                "ready": any(str(bar.get("bar_id")) in ready_bar_ids for bar in beam_bars),
                "calculated": any(str(bar.get("bar_id")) in calculated_bar_ids for bar in beam_bars),
                "bbs": len(bbs_by_beam.get(beam_id, [])) > 0,
                "excel": excel_block is not None and len(getattr(excel_block, "rows", []) or []) > 0,
            }
            present_categories = {category_for_role(bar.get("role")) for bar in beam_bars}
            missing_categories = [
                category for category in REINFORCEMENT_CATEGORIES if category not in present_categories
            ]
            missing_calculations = [
                str(bar.get("bar_id"))
                for bar in beam_bars
                if str(bar.get("bar_id")) not in calculated_bar_ids
            ]
            missing_outputs = []
            if not stage_status["bbs"]:
                missing_outputs.append("bbs")
            if not stage_status["excel"]:
                missing_outputs.append("excel")
            if schedule.get("row_count", len(schedule.get("rows") or [])) == 0:
                missing_outputs.append("beam_schedule_rows")

            completeness = round_pct(sum(stage_status.values()), len(self.STAGE_KEYS))
            reports.append(
                {
                    "beam_id": beam_id,
                    "beam_mark": schedule.get("beam_mark") or beam_id,
                    "stages": stage_status,
                    "overall_completeness_percent": completeness,
                    "missing_categories": missing_categories,
                    "missing_calculations": missing_calculations,
                    "missing_outputs": missing_outputs,
                    "bar_count": len(beam_bars),
                    "group_count": len(beam_groups),
                    "schedule_row_count": len(schedule.get("rows") or []),
                    "report_state": report.get("report_state") or schedule.get("schedule_state"),
                    "total_steel_weight_kg": schedule.get("total_steel_weight_kg"),
                }
            )

        return {
            "beam_count": len(reports),
            "beams": reports,
            "average_completeness_percent": round(
                sum(item["overall_completeness_percent"] for item in reports) / len(reports),
                2,
            )
            if reports
            else 0.0,
        }

    @staticmethod
    def _index_by_beam(records: List[dict[str, Any]], key: str) -> Dict[str, List[dict[str, Any]]]:
        grouped: Dict[str, List[dict[str, Any]]] = defaultdict(list)
        for record in records:
            beam_id = str(record.get(key) or record.get("beam_mark") or "")
            if beam_id:
                grouped[beam_id].append(record)
        return grouped

    @staticmethod
    def _stage_flag(records: List[dict[str, Any]], stage: str) -> bool:
        if not records:
            return False
        if stage == "geometry":
            for record in records:
                summary = record.get("upstream_status_summary") or record
                if summary.get("clear_span_mm") or summary.get("effective_span_mm"):
                    return True
                if str(record.get("association_status", "")).upper() == "VALID":
                    return True
            return False
        if stage == "specification":
            for record in records:
                if record.get("specification_id"):
                    return True
                traceability = record.get("traceability") or {}
                if traceability.get("specification_id"):
                    return True
            return False
        return True
