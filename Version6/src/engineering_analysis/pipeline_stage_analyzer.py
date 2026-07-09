"""Pipeline stage coverage and funnel analysis."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_analysis.coverage_collector import round_pct


class PipelineStageAnalyzer:
    """Compute stage coverage statistics and the engineering pipeline funnel."""

    STAGE_ORDER: tuple[tuple[str, str], ...] = (
        ("drawing_parser", "Drawing Objects"),
        ("engineering_objects", "Beam Objects"),
        ("property_graph", "Property Graph Nodes"),
        ("specifications", "Specifications"),
        ("geometry_association", "Geometry Associations"),
        ("calculation_context", "Calculation Contexts"),
        ("reinforcement_groups", "Reinforcement Groups"),
        ("normalized_bars", "Normalized Bars"),
        ("ready_for_calculation", "READY"),
        ("calculated_bars", "CALCULATED"),
        ("bbs_rows_written", "Written to BBS"),
        ("beam_schedule_rows", "Written to Beam Schedule"),
        ("excel_rows_written", "Written to Excel"),
    )

    def analyze(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        counts = self._stage_counts(snapshot)
        baseline = counts.get("drawing_parser") or counts.get("normalized_bars") or 1
        stage_report = self._build_stage_report(counts, baseline)
        funnel = self._build_funnel(counts)
        return {
            "baseline_count": baseline,
            "stage_counts": counts,
            "stage_coverage": stage_report,
            "pipeline_funnel": funnel,
        }

    def _stage_counts(self, snapshot: dict[str, Any]) -> Dict[str, int]:
        bars = snapshot.get("bars") or []
        groups = snapshot.get("groups") or []
        contexts = snapshot.get("contexts") or []
        beam_schedules = snapshot.get("beam_schedules") or []
        bbs_records = snapshot.get("bbs_records") or []
        schedule_rows = sum(len(item.get("rows") or []) for item in beam_schedules)

        return {
            "drawing_parser": int(snapshot.get("drawing_entities") or 0),
            "engineering_objects": len(snapshot.get("beam_ids") or []),
            "property_graph": int(snapshot.get("property_graph_nodes") or 0),
            "specifications": len(snapshot.get("specification_ids") or []),
            "geometry_association": int(snapshot.get("geometry_associations") or 0),
            "calculation_context": len(contexts),
            "reinforcement_groups": len(groups) or len(snapshot.get("bar_groups") or []),
            "normalized_bars": len(bars),
            "ready_for_calculation": len(snapshot.get("ready_bar_ids") or []),
            "calculated_bars": len(snapshot.get("calculated_bar_ids") or []),
            "bbs_rows_written": len(snapshot.get("bbs_bar_ids") or []) or len(bbs_records),
            "beam_schedule_rows": schedule_rows,
            "excel_rows_written": int(snapshot.get("excel_row_count") or 0),
        }

    def _build_stage_report(self, counts: Dict[str, int], baseline: int) -> Dict[str, Any]:
        report: Dict[str, Any] = {}
        previous_count = baseline
        cumulative_loss = 0
        for stage_key, _label in self.STAGE_ORDER:
            count = counts.get(stage_key, 0)
            loss_from_previous = max(previous_count - count, 0)
            cumulative_loss += loss_from_previous
            report[stage_key] = {
                "count": count,
                "coverage_percent": round_pct(count, baseline),
                "loss_from_previous_stage": loss_from_previous,
                "cumulative_loss": cumulative_loss,
            }
            previous_count = count
        return report

    def _build_funnel(self, counts: Dict[str, int]) -> dict[str, Any]:
        transitions: List[dict[str, Any]] = []
        stages: List[dict[str, Any]] = []
        ordered_counts = [counts.get(key, 0) for key, _label in self.STAGE_ORDER]

        for index, (stage_key, label) in enumerate(self.STAGE_ORDER):
            count = ordered_counts[index]
            stages.append({"stage": stage_key, "label": label, "count": count})
            if index == 0:
                continue
            previous_count = ordered_counts[index - 1]
            loss = max(previous_count - count, 0)
            transitions.append(
                {
                    "from_stage": self.STAGE_ORDER[index - 1][0],
                    "to_stage": stage_key,
                    "from_label": self.STAGE_ORDER[index - 1][1],
                    "to_label": label,
                    "from_count": previous_count,
                    "to_count": count,
                    "loss": loss,
                    "loss_percent": round_pct(loss, previous_count) if previous_count else 0.0,
                    "survival_percent": round_pct(count, previous_count) if previous_count else 100.0,
                }
            )

        return {
            "stages": stages,
            "transitions": transitions,
            "starting_count": ordered_counts[0] if ordered_counts else 0,
            "ending_count": ordered_counts[-1] if ordered_counts else 0,
        }
