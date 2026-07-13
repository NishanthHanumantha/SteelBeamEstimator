"""Audit the calculation context pipeline stage."""

from __future__ import annotations
from typing import Any, Dict, List


class ContextPipelineAuditor:
    def audit(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        ctx = snapshot.get("calculation_contexts") or {}
        results = ctx.get("results") or ctx.get("contexts") or []
        statuses: Dict[str, int] = {}
        for r in results:
            s = str(r.get("status") or r.get("context_status") or "UNKNOWN")
            statuses[s] = statuses.get(s, 0) + 1
        return {
            "total_contexts": len(results),
            "status_distribution": statuses,
            "gap_summary": (
                "Calculation contexts only created for bars that have engineering objects. "
                "STIRRUP contexts may be missing beam_section_width/depth values needed for "
                "transverse perimeter calculation."
            ),
        }
