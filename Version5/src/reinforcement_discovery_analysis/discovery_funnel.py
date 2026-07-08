"""Reinforcement discovery funnel analysis."""

from __future__ import annotations

from typing import Any, Dict, List

from src.reinforcement_discovery_analysis.discovery_collector import FUNNEL_STAGES, round_pct


class DiscoveryFunnelAnalyzer:
    """Build discovery funnel statistics from inventory pipeline traces."""

    STAGE_FLAGS = {
        "drawing_callouts": lambda item: True,
        "detected": lambda item: item.get("pipeline_trace", {}).get("text_detected"),
        "classified": lambda item: item.get("pipeline_trace", {}).get("classified"),
        "associated": lambda item: item.get("pipeline_trace", {}).get("associated"),
        "engineering_objects": lambda item: item.get("pipeline_trace", {}).get("engineering_object_created")
        or bool(item.get("engineering_object_id")),
        "normalized": lambda item: bool(item.get("normalized_bar_id")),
        "ready": lambda item: item.get("pipeline_trace", {}).get("ready"),
        "calculated": lambda item: item.get("pipeline_trace", {}).get("calculated"),
        "written_to_bbs": lambda item: item.get("pipeline_trace", {}).get("written_to_bbs"),
        "written_to_excel": lambda item: item.get("pipeline_trace", {}).get("written_to_excel"),
    }

    def analyze(self, inventory: List[dict[str, Any]]) -> dict[str, Any]:
        counts = self._stage_counts(inventory)
        transitions = self._transitions(counts)
        return {
            "baseline_count": counts.get("drawing_callouts", 0),
            "stage_counts": counts,
            "stages": [
                {"stage": stage_key, "label": label, "count": counts.get(stage_key, 0)}
                for stage_key, label in FUNNEL_STAGES
            ],
            "transitions": transitions,
        }

    def _stage_counts(self, inventory: List[dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for stage_key, _label in FUNNEL_STAGES:
            predicate = self.STAGE_FLAGS[stage_key]
            counts[stage_key] = sum(1 for item in inventory if predicate(item))
        return counts

    def _transitions(self, counts: Dict[str, int]) -> List[dict[str, Any]]:
        transitions: List[dict[str, Any]] = []
        ordered = [(key, label) for key, label in FUNNEL_STAGES]
        for index in range(1, len(ordered)):
            from_key, from_label = ordered[index - 1]
            to_key, to_label = ordered[index]
            from_count = counts.get(from_key, 0)
            to_count = counts.get(to_key, 0)
            loss = max(from_count - to_count, 0)
            transitions.append(
                {
                    "from_stage": from_key,
                    "to_stage": to_key,
                    "from_label": from_label,
                    "to_label": to_label,
                    "from_count": from_count,
                    "to_count": to_count,
                    "loss": loss,
                    "loss_percent": round_pct(loss, from_count),
                    "survival_percent": round_pct(to_count, from_count),
                }
            )
        return transitions
