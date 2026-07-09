"""Estimate missing engineering content and rank gaps by impact."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_analysis.coverage_collector import REINFORCEMENT_CATEGORIES, round_pct


class EngineeringGapAnalyzer:
    """Rank engineering gaps using deterministic heuristics."""

    IMPACT_WEIGHTS = {
        "Very High": 4,
        "High": 3,
        "Medium": 2,
        "Low": 1,
    }

    CATEGORY_IMPACT = {
        "Top Main": "Very High",
        "Bottom Main": "Very High",
        "Top Extra": "High",
        "Bottom Extra": "High",
        "Stirrups": "Medium",
        "Side Face Bars": "Medium",
        "Support Bars": "Medium",
        "Curtailment Bars": "Low",
        "Lap Bars": "Low",
        "Hooks": "Low",
        "Anchorage": "Low",
        "Spacer Bars": "Low",
        "Chair Bars": "Low",
        "Distribution Bars": "Low",
        "Other": "Low",
    }

    def analyze(
        self,
        reinforcement: dict[str, Any],
        beam_coverage: dict[str, Any],
        calculation_states: dict[str, Any],
        pipeline: dict[str, Any],
    ) -> dict[str, Any]:
        category_gaps = self._category_gaps(reinforcement, beam_coverage)
        process_gaps = self._process_gaps(calculation_states, pipeline)
        ranked = sorted(
            category_gaps + process_gaps,
            key=lambda item: (
                self.IMPACT_WEIGHTS.get(item["estimated_impact"], 0),
                item.get("estimated_downstream_effect_percent", 0),
                item.get("count", 0),
            ),
            reverse=True,
        )
        return {
            "gaps": ranked,
            "category_gaps": category_gaps,
            "process_gaps": process_gaps,
            "total_gaps": len(ranked),
        }

    def _category_gaps(
        self,
        reinforcement: dict[str, Any],
        beam_coverage: dict[str, Any],
    ) -> List[dict[str, Any]]:
        gaps: List[dict[str, Any]] = []
        beam_count = max(beam_coverage.get("beam_count") or 1, 1)
        categories = reinforcement.get("categories") or []
        for item in categories:
            category = item.get("category")
            if category not in REINFORCEMENT_CATEGORIES:
                continue
            missing_beams = sum(
                1
                for beam in beam_coverage.get("beams") or []
                if category in (beam.get("missing_categories") or [])
            )
            if missing_beams <= 0 and item.get("found", 0) > 0:
                continue
            downstream = round_pct(missing_beams, beam_count)
            gaps.append(
                {
                    "gap_type": "missing_reinforcement_category",
                    "title": f"Missing {category}",
                    "category": category,
                    "count": missing_beams,
                    "estimated_impact": self.CATEGORY_IMPACT.get(category, "Low"),
                    "estimated_downstream_effect_percent": downstream,
                    "details": {
                        "found_in_pipeline": item.get("found", 0),
                        "written_to_schedule": item.get("written", 0),
                    },
                }
            )
        return gaps

    def _process_gaps(
        self,
        calculation_states: dict[str, Any],
        pipeline: dict[str, Any],
    ) -> List[dict[str, Any]]:
        gaps: List[dict[str, Any]] = []
        deferred = calculation_states.get("deferred_analysis") or {}
        blocked = calculation_states.get("blocked_analysis") or {}
        stage_counts = pipeline.get("stage_counts") or {}
        normalized = max(stage_counts.get("normalized_bars", 0), 1)

        if deferred.get("total_deferred", 0) > 0:
            top_reason = (deferred.get("reasons") or [{}])[0]
            gaps.append(
                {
                    "gap_type": "deferred_calculations",
                    "title": top_reason.get("reason") or "Deferred calculations",
                    "count": deferred.get("total_deferred", 0),
                    "estimated_impact": "High",
                    "estimated_downstream_effect_percent": round_pct(
                        deferred.get("total_deferred", 0),
                        normalized,
                    ),
                    "details": {"top_reason": top_reason},
                }
            )

        if blocked.get("total_blocked", 0) > 0:
            top_reason = (blocked.get("top_blocking_reasons") or [{}])[0]
            gaps.append(
                {
                    "gap_type": "blocked_calculations",
                    "title": top_reason.get("reason") or "Blocked calculations",
                    "count": blocked.get("total_blocked", 0),
                    "estimated_impact": "Medium",
                    "estimated_downstream_effect_percent": round_pct(
                        blocked.get("total_blocked", 0),
                        normalized,
                    ),
                    "details": {"top_reason": top_reason},
                }
            )

        transitions = (pipeline.get("pipeline_funnel") or {}).get("transitions") or []
        for transition in transitions:
            if transition.get("loss", 0) <= 0:
                continue
            gaps.append(
                {
                    "gap_type": "pipeline_transition_loss",
                    "title": f"Loss at {transition.get('to_label')}",
                    "count": transition.get("loss", 0),
                    "estimated_impact": "Medium" if transition.get("loss_percent", 0) >= 20 else "Low",
                    "estimated_downstream_effect_percent": transition.get("loss_percent", 0),
                    "details": transition,
                }
            )
        return gaps
