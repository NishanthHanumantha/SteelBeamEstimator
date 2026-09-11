"""
engineering_reinforcement_builder.py — Build complete R1BeamReinforcementModel per beam.

EVERY beam receives a model.  No placeholders.  No skipped beams.
The model is downstream-compatible with L.2's BeamReinforcementModel contract.
"""

from __future__ import annotations

import logging
import uuid
from typing import Dict, List

from .reinforcement_models import (
    BeamDetail,
    ReinforcementAnnotation,
    ReinforcementGroup,
    R1BeamReinforcementModel,
    ROLE_UNKNOWN,
)

log = logging.getLogger(__name__)


def _pct(numerator: int, denominator: int) -> float:
    return round(100.0 * numerator / denominator, 1) if denominator else 0.0


class EngineeringReinforcementBuilder:
    """Creates one R1BeamReinforcementModel per beam."""

    def build(
        self,
        details:          List[BeamDetail],
        beam_annotations: Dict[str, List[ReinforcementAnnotation]],
        beam_groups:      Dict[str, Dict[str, ReinforcementGroup]],
    ) -> Dict[str, R1BeamReinforcementModel]:
        """Return beam_id → R1BeamReinforcementModel."""
        result: Dict[str, R1BeamReinforcementModel] = {}

        for detail in details:
            beam_id = detail.beam_id
            anns    = beam_annotations.get(beam_id, [])
            groups  = beam_groups.get(beam_id, {})

            rebar_anns  = [a for a in anns if a.is_reinforcement]
            classified  = [a for a in rebar_anns if a.role != ROLE_UNKNOWN]
            coverage    = _pct(len(classified), len(rebar_anns))
            complete    = coverage >= 50.0 and len(rebar_anns) >= 1

            model = R1BeamReinforcementModel(
                beam_id                 = beam_id,
                beam_mark               = detail.beam_mark,
                model_id                = f"R1MODEL-{beam_id}-{uuid.uuid4().hex[:8]}",
                section                 = detail.section,
                groups                  = groups,
                all_annotations         = anns,
                coverage_pct            = coverage,
                classification_complete = complete,
            )
            result[beam_id] = model

        log.info(
            "EngineeringReinforcementBuilder: %d models built (%d complete)",
            len(result),
            sum(1 for m in result.values() if m.classification_complete),
        )
        return result
