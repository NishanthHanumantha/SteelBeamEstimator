"""
reinforcement_relationship_builder.py — Build engineering relationships.

Relationships:
  - Bar BELONGS_TO Beam
  - Stirrup CONFINES Beam
  - Development bar EXTENDS_FROM Main bar
  - Spacer SUPPORTS Group
"""

from __future__ import annotations

import logging
import uuid
from typing import Dict, List

from .reinforcement_models import (
    ReinforcementAnnotation,
    ReinforcementGroup,
    ROLE_STIRRUP, ROLE_SPACER, ROLE_DEVELOPMENT,
    ROLE_TOP_MAIN, ROLE_BOTTOM_MAIN,
)

log = logging.getLogger(__name__)


def _rel(subject: str, predicate: str, obj: str, meta: dict = None) -> dict:
    return {
        "relationship_id": f"REL-{uuid.uuid4().hex[:8]}",
        "subject":         subject,
        "predicate":       predicate,
        "object":          obj,
        "meta":            meta or {},
    }


class ReinforcementRelationshipBuilder:
    """Builds semantic engineering relationships between reinforcement objects."""

    def build(
        self,
        beam_groups: Dict[str, Dict[str, ReinforcementGroup]],
    ) -> Dict[str, List[dict]]:
        """Return beam_id → [relationship_dict, ...]"""
        result: Dict[str, List[dict]] = {}

        for beam_id, groups in beam_groups.items():
            rels: List[dict] = []

            for role, grp in groups.items():
                for bar in grp.bars:
                    rels.append(_rel(
                        bar.bar_label or bar.annotation_id,
                        "BELONGS_TO",
                        beam_id,
                        {"role": role, "group_id": grp.group_id},
                    ))

                if role == ROLE_STIRRUP:
                    rels.append(_rel(
                        grp.group_id, "CONFINES", beam_id,
                        {"spacing_mm": [b.spacing_mm for b in grp.bars if b.spacing_mm]},
                    ))

                if role == ROLE_DEVELOPMENT:
                    top_main = groups.get(ROLE_TOP_MAIN)
                    bot_main = groups.get(ROLE_BOTTOM_MAIN)
                    ref_grp  = top_main or bot_main
                    if ref_grp:
                        rels.append(_rel(
                            grp.group_id, "EXTENDS_FROM", ref_grp.group_id,
                        ))

                if role == ROLE_SPACER:
                    bot_main = groups.get(ROLE_BOTTOM_MAIN)
                    if bot_main:
                        rels.append(_rel(
                            grp.group_id, "SUPPORTS", bot_main.group_id,
                        ))

            result[beam_id] = rels

        total = sum(len(v) for v in result.values())
        log.info("ReinforcementRelationshipBuilder: %d relationships", total)
        return result
