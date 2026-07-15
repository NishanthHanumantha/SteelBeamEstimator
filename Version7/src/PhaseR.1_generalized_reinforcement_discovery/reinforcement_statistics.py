"""
reinforcement_statistics.py — Coverage and distribution statistics.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Dict, List

from .reinforcement_models import (
    BeamDetail,
    ReinforcementAnnotation,
    ReinforcementGroup,
    R1BeamReinforcementModel,
    ROLE_TOP_MAIN, ROLE_BOTTOM_MAIN,
    ROLE_TOP_EXTRA, ROLE_BOTTOM_EXTRA,
    ROLE_STIRRUP, ROLE_SPACER, ROLE_SIDE_FACE,
    ROLE_DEVELOPMENT, ROLE_UNKNOWN,
)

log = logging.getLogger(__name__)


class ReinforcementStatistics:
    """Aggregates statistics across all beams."""

    def compute(
        self,
        details:          List[BeamDetail],
        beam_annotations: Dict[str, List[ReinforcementAnnotation]],
        beam_groups:      Dict[str, Dict[str, ReinforcementGroup]],
        models:           Dict[str, R1BeamReinforcementModel],
    ) -> dict:
        total_beams   = len(details)
        total_anns    = sum(len(v) for v in beam_annotations.values())
        rebar_anns    = sum(
            1 for anns in beam_annotations.values()
            for a in anns if a.is_reinforcement
        )
        classified    = sum(
            1 for anns in beam_annotations.values()
            for a in anns if a.is_reinforcement and a.role != ROLE_UNKNOWN
        )
        unknown_anns  = rebar_anns - classified
        coverage_pct  = round(100.0 * classified / rebar_anns, 1) if rebar_anns else 0.0
        unknown_pct   = round(100.0 * unknown_anns / rebar_anns, 1) if rebar_anns else 0.0

        role_counter: Counter = Counter()
        for grp_dict in beam_groups.values():
            for role, grp in grp_dict.items():
                role_counter[role] += grp.total_quantity

        beams_with_top    = sum(1 for m in models.values() if ROLE_TOP_MAIN    in m.groups)
        beams_with_bottom = sum(1 for m in models.values() if ROLE_BOTTOM_MAIN in m.groups)
        beams_with_stir   = sum(1 for m in models.values() if ROLE_STIRRUP     in m.groups)
        beams_complete    = sum(1 for m in models.values() if m.classification_complete)

        avg_groups = round(
            sum(len(g) for g in beam_groups.values()) / total_beams, 2
        ) if total_beams else 0.0

        stats = {
            "total_beams":            total_beams,
            "total_annotations":      total_anns,
            "total_rebar_annotations": rebar_anns,
            "classified_annotations": classified,
            "unknown_annotations":    unknown_anns,
            "coverage_pct":           coverage_pct,
            "unknown_pct":            unknown_pct,
            "beams_with_top_main":    beams_with_top,
            "beams_with_bottom_main": beams_with_bottom,
            "beams_with_stirrups":    beams_with_stir,
            "beams_classification_complete": beams_complete,
            "avg_groups_per_beam":    avg_groups,
            "role_distribution":      dict(role_counter.most_common()),
            "top_bar_quantity":       role_counter.get(ROLE_TOP_MAIN, 0),
            "bottom_bar_quantity":    role_counter.get(ROLE_BOTTOM_MAIN, 0),
            "top_extra_quantity":     role_counter.get(ROLE_TOP_EXTRA, 0),
            "bottom_extra_quantity":  role_counter.get(ROLE_BOTTOM_EXTRA, 0),
            "stirrup_quantity":       role_counter.get(ROLE_STIRRUP, 0),
            "spacer_quantity":        role_counter.get(ROLE_SPACER, 0),
            "side_face_quantity":     role_counter.get(ROLE_SIDE_FACE, 0),
            "development_quantity":   role_counter.get(ROLE_DEVELOPMENT, 0),
        }
        log.info(
            "Statistics: %d beams, coverage %.1f%%, %d with TOP_MAIN, %d with BOTTOM_MAIN",
            total_beams, coverage_pct, beams_with_top, beams_with_bottom,
        )
        return stats
