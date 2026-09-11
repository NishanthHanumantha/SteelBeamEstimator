"""
reinforcement_group_builder.py — Build one engineering group per role per beam.

Each ReinforcementGroup aggregates all annotations that share the same
semantic role for a given beam.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from typing import Dict, List

from .reinforcement_models import (
    ReinforcementAnnotation,
    ReinforcementGroup,
    ROLE_UNKNOWN,
)

log = logging.getLogger(__name__)


class ReinforcementGroupBuilder:
    """Groups annotations by role into ReinforcementGroup objects."""

    def build(
        self,
        beam_annotations: Dict[str, List[ReinforcementAnnotation]],
    ) -> Dict[str, Dict[str, ReinforcementGroup]]:
        """Return beam_id → {role → ReinforcementGroup}."""
        result: Dict[str, Dict[str, ReinforcementGroup]] = {}

        for beam_id, anns in beam_annotations.items():
            role_map: Dict[str, List[ReinforcementAnnotation]] = defaultdict(list)
            for ann in anns:
                if ann.is_reinforcement:
                    role_map[ann.role].append(ann)

            groups: Dict[str, ReinforcementGroup] = {}
            for role, bars in role_map.items():
                grp = ReinforcementGroup(
                    group_id       = f"GRP-{beam_id}-{role}-{uuid.uuid4().hex[:6]}",
                    beam_id        = beam_id,
                    role           = role,
                    bars           = bars,
                    total_quantity = sum(b.quantity for b in bars),
                    diameters_mm   = sorted({b.diameter_mm for b in bars}),
                    labels         = [b.bar_label for b in bars if b.bar_label],
                )
                groups[role] = grp

            result[beam_id] = groups

        total_groups = sum(len(g) for g in result.values())
        log.info("ReinforcementGroupBuilder: %d groups across %d beams", total_groups, len(result))
        return result
