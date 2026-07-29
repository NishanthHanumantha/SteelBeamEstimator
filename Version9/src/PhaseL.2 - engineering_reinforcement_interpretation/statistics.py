"""Compute interpretation statistics."""

from __future__ import annotations

from typing import Any, Dict, List

from beam_reinforcement_model import BeamReinforcementModel, ROLE_UNKNOWN, ALL_ROLES


class InterpretationStatistics:
    def build(self, models: List[BeamReinforcementModel]) -> Dict[str, Any]:
        total_beams = len(models)
        total_bars = sum(len(m.all_bars()) for m in models)
        classified = sum(
            sum(1 for b in m.all_bars() if b.semantic_role != ROLE_UNKNOWN) for m in models
        )
        corrected = sum(
            sum(1 for b in m.all_bars() if b.is_corrected) for m in models
        )
        reference_anchored = sum(
            sum(1 for b in m.all_bars() if b.is_reference_anchored) for m in models
        )
        roles_dist: Dict[str, int] = {r: 0 for r in ALL_ROLES}
        for m in models:
            for b in m.all_bars():
                roles_dist[b.semantic_role] = roles_dist.get(b.semantic_role, 0) + 1

        confidence: Dict[str, int] = {}
        for m in models:
            for b in m.all_bars():
                c = b.classification_confidence
                confidence[c] = confidence.get(c, 0) + 1

        return {
            "total_beams": total_beams,
            "total_bars": total_bars,
            "classified_bars": classified,
            "unclassified_bars": total_bars - classified,
            "classification_rate_percent": round(100 * classified / max(total_bars, 1), 2),
            "pipeline_corrections": corrected,
            "reference_anchored_bars": reference_anchored,
            "benchmark_beams_complete": sum(1 for m in models if m.is_benchmark_beam and m.classification_complete),
            "roles_distribution": roles_dist,
            "confidence_distribution": confidence,
        }
