"""Aggregate engineering statistics, health scores, and root causes."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_analysis.coverage_collector import round_pct


class EngineeringStatistics:
    """Compute subsystem health scores and root-cause summaries."""

    SUBSYSTEMS = (
        ("parser", "drawing_parser"),
        ("engineering_objects", "engineering_objects"),
        ("property_graph", "property_graph"),
        ("specifications", "specifications"),
        ("geometry", "geometry_association"),
        ("reinforcement", "normalized_bars"),
        ("calculations", "calculated_bars"),
        ("bbs", "bbs_rows_written"),
        ("excel", "excel_rows_written"),
    )

    def build(
        self,
        snapshot: dict[str, Any],
        pipeline: dict[str, Any],
        reinforcement: dict[str, Any],
        calculation_states: dict[str, Any],
        beam_coverage: dict[str, Any],
        losses: dict[str, Any],
        gaps: dict[str, Any],
    ) -> dict[str, Any]:
        health = self._health_scores(pipeline)
        root_causes = self._root_causes(calculation_states, losses, gaps, pipeline)
        statistics = {
            "beam_count": len(snapshot.get("beam_ids") or []),
            "normalized_bar_count": len(snapshot.get("bars") or []),
            "ready_bar_count": len(snapshot.get("ready_bar_ids") or []),
            "calculated_bar_count": len(snapshot.get("calculated_bar_ids") or []),
            "bbs_record_count": len(snapshot.get("bbs_records") or []),
            "schedule_row_count": pipeline.get("stage_counts", {}).get("beam_schedule_rows", 0),
            "excel_row_count": snapshot.get("excel_row_count", 0),
            "average_beam_completeness_percent": beam_coverage.get("average_completeness_percent", 0.0),
            "deferred_bar_count": calculation_states.get("deferred_analysis", {}).get("total_deferred", 0),
            "blocked_item_count": calculation_states.get("blocked_analysis", {}).get("total_blocked", 0),
            "categories_found": sum(1 for item in reinforcement.get("categories", []) if item.get("found", 0) > 0),
            "categories_written": sum(1 for item in reinforcement.get("categories", []) if item.get("written", 0) > 0),
            "total_engineering_loss": losses.get("total_lost_to_excel", 0),
        }
        return {
            "statistics": statistics,
            "engineering_health_score": health,
            "root_cause_summary": root_causes,
        }

    def _health_scores(self, pipeline: dict[str, Any]) -> dict[str, Any]:
        counts = pipeline.get("stage_counts") or {}
        bars = max(counts.get("normalized_bars", 0), 1)
        beams = max(counts.get("engineering_objects", 0), 1)
        contexts = max(counts.get("calculation_context", 0), 1)
        calculated = counts.get("calculated_bars", 0)
        bbs = counts.get("bbs_rows_written", 0)
        schedule_rows = counts.get("beam_schedule_rows", 0)
        excel_rows = counts.get("excel_rows_written", 0)
        drawing = max(counts.get("drawing_parser", 0), 1)

        subsystem_scores: Dict[str, float] = {
            "parser": round_pct(bars, drawing),
            "engineering_objects": round_pct(counts.get("engineering_objects", 0), beams),
            "property_graph": round_pct(counts.get("property_graph", 0), bars * 3),
            "specifications": round_pct(counts.get("specifications", 0), bars),
            "geometry": round_pct(counts.get("geometry_association", 0), contexts),
            "reinforcement": round_pct(bars, bars),
            "calculations": round_pct(calculated, bars),
            "bbs": round_pct(bbs, max(calculated, 1)),
            "excel": round_pct(excel_rows, max(schedule_rows, 1)),
        }
        overall_values = list(subsystem_scores.values())
        overall = round(sum(overall_values) / len(overall_values), 2) if overall_values else 0.0
        return {
            "subsystems": subsystem_scores,
            "overall": overall,
            "scale": "0-100",
            "method": "observed_coverage_only",
        }

    def _root_causes(
        self,
        calculation_states: dict[str, Any],
        losses: dict[str, Any],
        gaps: dict[str, Any],
        pipeline: dict[str, Any],
    ) -> dict[str, Any]:
        candidates: List[dict[str, Any]] = []

        for index, reason in enumerate(calculation_states.get("deferred_analysis", {}).get("reasons") or [], start=1):
            candidates.append(
                {
                    "rank": index,
                    "issue": reason.get("reason"),
                    "impact": "High" if reason.get("count", 0) >= 5 else "Medium",
                    "estimated_downstream_effect_percent": round_pct(
                        reason.get("count", 0),
                        max(pipeline.get("stage_counts", {}).get("normalized_bars", 0), 1),
                    ),
                    "count": reason.get("count", 0),
                    "source": "deferred_analysis",
                }
            )

        for index, reason in enumerate(
            calculation_states.get("blocked_analysis", {}).get("top_blocking_reasons") or [],
            start=1,
        ):
            candidates.append(
                {
                    "rank": index,
                    "issue": reason.get("reason"),
                    "impact": "Medium",
                    "estimated_downstream_effect_percent": round_pct(
                        reason.get("count", 0),
                        max(pipeline.get("stage_counts", {}).get("normalized_bars", 0), 1),
                    ),
                    "count": reason.get("count", 0),
                    "source": "blocked_analysis",
                }
            )

        for transition in losses.get("transitions") or []:
            if transition.get("lost", 0) <= 0:
                continue
            top_reason = (transition.get("reasons") or [{}])[0].get("reason", transition.get("transition"))
            candidates.append(
                {
                    "issue": top_reason,
                    "impact": "High" if transition.get("loss_percent", 0) >= 25 else "Medium",
                    "estimated_downstream_effect_percent": transition.get("loss_percent", 0),
                    "count": transition.get("lost", 0),
                    "source": "engineering_loss_report",
                    "transition": transition.get("transition"),
                }
            )

        for gap in gaps.get("gaps") or []:
            candidates.append(
                {
                    "issue": gap.get("title"),
                    "impact": gap.get("estimated_impact"),
                    "estimated_downstream_effect_percent": gap.get("estimated_downstream_effect_percent", 0),
                    "count": gap.get("count", 0),
                    "source": "engineering_gap_analysis",
                }
            )

        ranked = sorted(
            candidates,
            key=lambda item: (
                {"Very High": 4, "High": 3, "Medium": 2, "Low": 1}.get(str(item.get("impact")), 0),
                item.get("estimated_downstream_effect_percent", 0),
                item.get("count", 0),
            ),
            reverse=True,
        )
        for index, item in enumerate(ranked[:10], start=1):
            item["rank"] = index
        return {
            "top_issues": ranked[:10],
            "primary_root_cause": ranked[0] if ranked else None,
        }
