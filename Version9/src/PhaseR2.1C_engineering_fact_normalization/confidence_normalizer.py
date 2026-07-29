"""
confidence_normalizer.py — Normalize confidence to apply to role + placement ONLY.
MODEL_VERSION: 7.12.0

In R.2.1B, confidence was assigned to the full semantic object.
In R.2.1C, confidence is scoped specifically to:
  - Role identification reliability
  - Placement identification reliability

NOT to intent (intent is always UNKNOWN at this stage).
"""
from __future__ import annotations

from typing import Any, Dict

from .fact_models import (
    CONF_HIGH,
    CONF_MEDIUM,
    CONF_LOW,
    ROLE_STIRRUP,
    ROLE_SIDE_FACE,
    PLACEMENT_UNKNOWN,
    ROLE_UNKNOWN,
)


class ConfidenceNormalizer:
    """
    Recompute confidence to reflect only role + placement certainty.

    Returns (confidence: str, notes: list[str]).
    """

    def normalize(
        self,
        eso: Dict[str, Any],
        role: str,
        placement: str,
    ) -> tuple:
        notes = []
        eso_conf = eso.get("confidence", CONF_LOW) or CONF_LOW

        # Settled roles: full confidence in role, placement irrelevant
        if role == ROLE_STIRRUP:
            return CONF_HIGH, ["STIRRUP: HIGH confidence (transverse, explicit)"]

        if role == ROLE_SIDE_FACE:
            return CONF_HIGH, ["SIDE_FACE: HIGH confidence (S.F.R. explicit modifier)"]

        # Unknown role: low confidence
        if role == ROLE_UNKNOWN:
            notes.append("UNKNOWN role: LOW confidence")
            return CONF_LOW, notes

        # Unknown placement reduces confidence
        if placement == PLACEMENT_UNKNOWN:
            if eso_conf == CONF_HIGH:
                conf = CONF_MEDIUM
                notes.append(
                    f"ESO confidence was HIGH but placement=UNKNOWN reduces to MEDIUM"
                )
            else:
                conf = CONF_LOW
                notes.append(
                    f"Placement=UNKNOWN with ESO confidence={eso_conf!r}: LOW"
                )
            return conf, notes

        # Known role + known placement → preserve ESO confidence
        conf_map = {CONF_HIGH: CONF_HIGH, CONF_MEDIUM: CONF_MEDIUM, CONF_LOW: CONF_LOW}
        conf = conf_map.get(eso_conf, CONF_MEDIUM)
        notes.append(
            f"Role={role!r} + Placement={placement!r}: confidence preserved as {conf}"
        )
        return conf, notes
