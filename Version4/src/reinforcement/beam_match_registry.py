"""Registry export for committed beam matches."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement.beam_match import build_matching_summary


class BeamMatchRegistry:
    """Build project-level beam match registry."""

    @staticmethod
    def build(
        beam_matches: List[dict[str, Any]],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        entries = [
            {
                "beam_match_id": item.get("beam_match_id"),
                "detail_identity_id": item.get("detail_identity_id"),
                "detail_context_id": item.get("detail_context_id"),
                "match_decision_id": item.get("match_decision_id"),
                "beam_context_id": item.get("beam_context_id"),
                "beam_mark": item.get("beam_mark"),
                "match_status": item.get("match_status"),
                "confidence": item.get("confidence"),
                "confidence_level": item.get("confidence_level"),
                "algorithm_version": item.get("algorithm_version"),
                "engineering_status": item.get("engineering_status"),
            }
            for item in beam_matches
        ]
        summary = build_matching_summary(beam_matches)
        return {
            "namespace": "BEAM_MATCH",
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
            "match_count": len(entries),
            "matched_beam_count": summary["matched_beam_count"],
            "matching_progress": summary["matching_progress"],
            "beam_matches": entries,
        }

    @staticmethod
    def build_summary_export(
        beam_matches: List[dict[str, Any]],
        decisions: List[dict[str, Any]],
    ) -> dict[str, Any]:
        from src.reinforcement.beam_match import EXECUTION_STATUS_EXECUTED
        from src.reinforcement.match_decision_quality import DecisionQualityStatus

        eligible = sum(
            1
            for d in decisions
            if d.get("decision_quality", {}).get("quality_status")
            == DecisionQualityStatus.ENGINEERING_READY.value
        )
        executed = sum(
            1 for d in decisions if d.get("execution_status") == EXECUTION_STATUS_EXECUTED
        )
        summary = build_matching_summary(beam_matches)
        return {
            "phase": "Phase G.3",
            "eligible_decision_count": eligible,
            "executed_decision_count": executed,
            "beam_match_count": len(beam_matches),
            **summary,
        }
