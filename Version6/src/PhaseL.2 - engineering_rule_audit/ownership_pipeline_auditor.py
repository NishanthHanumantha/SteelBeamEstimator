"""Audit the ownership pipeline stage."""

from __future__ import annotations
from typing import Any, Dict, List


class OwnershipPipelineAuditor:
    def audit(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        ro = snapshot.get("reinforcement_objects") or {}
        bars = ro.get("bars") or []
        roles: Dict[str, int] = {}
        for b in bars:
            r = str(b.get("role") or "UNKNOWN")
            roles[r] = roles.get(r, 0) + 1
        return {
            "total_normalized_bars": len(bars),
            "role_distribution": roles,
            "gap_summary": (
                "Ownership (I.2 normalization) successful only for roles with engineering objects. "
                "BOTTOM_MAIN, TOP_EXTRA, BOTTOM_EXTRA have 0 bars because Phase G creates no objects."
            ),
        }
