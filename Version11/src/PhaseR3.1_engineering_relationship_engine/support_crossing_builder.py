"""
support_crossing_builder.py — Determine which supports a bar crosses.
MODEL_VERSION: 8.1.0

A bar "crosses" a support if its normalized extent reaches into the support zone.
This is purely geometric evidence — no engineering intent inferred.

SupportCrossing tells R.4:
  - Whether this bar reaches the left column
  - Whether this bar reaches the right column
  - How far into each support zone it extends

This is key evidence for R.4's intent resolution:
  - Bars crossing both supports → candidate for CONTINUOUS / MAIN
  - Bars crossing one support → candidate for SUPPORT / CURTAILED
  - Bars not crossing any support → candidate for EXTRA / MIDSPAN
  (But R.4 makes these interpretations, NOT R.3.1)
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from .relationship_models import (
    CONF_HIGH, CONF_MEDIUM, CONF_LOW,
    PhysicalBar, SupportCrossing,
)


class SupportCrossingBuilder:
    """
    Compute SupportCrossing for a PhysicalBar against beam supports.
    """

    def build(
        self,
        bar:          PhysicalBar,
        support_data: List[Dict[str, Any]],
    ) -> List[SupportCrossing]:
        crossings: List[SupportCrossing] = []

        ns = bar.normalized_start
        ne = bar.normalized_end

        for sup in support_data:
            sup_type  = str(sup.get("support_type") or "")
            sup_id    = str(sup.get("support_id") or "")
            zone_s    = float(sup.get("zone_start_fraction") or 0.0)
            zone_e    = float(sup.get("zone_end_fraction") or 0.0)

            # Does bar reach into this support zone?
            if "LEFT" in sup_type:
                crosses = ns <= zone_e
                depth   = max(0.0, zone_e - ns) if crosses else 0.0
            elif "RIGHT" in sup_type:
                crosses = ne >= zone_s
                depth   = max(0.0, ne - zone_s) if crosses else 0.0
            else:
                crosses = (ns <= zone_e and ne >= zone_s)
                depth   = max(0.0, min(ne, zone_e) - max(ns, zone_s))

            conf = CONF_HIGH if depth > 0.01 else CONF_MEDIUM

            crossings.append(SupportCrossing(
                crossing_id         = f"CROSS::{uuid.uuid4().hex[:8].upper()}",
                bar_id              = bar.bar_id,
                beam_id             = bar.beam_id,
                support_id          = sup_id,
                support_type        = sup_type,
                crosses             = crosses,
                normalized_depth    = round(depth, 4),
                crossing_confidence = conf,
            ))

        return crossings
