"""Frequency analysis helpers for notation inventory."""
from __future__ import annotations

from typing import Any, Dict, List

from .notation_models import NotationGroup


class NotationFrequencyAnalyzer:

    def analyze(
        self,
        groups: List[NotationGroup],
        support: Dict[str, Dict],
        categories: Dict[str, str],
    ) -> Dict[str, Any]:
        top = [
            {
                "notation": g.normalized_notation,
                "frequency": g.frequency,
                "category": categories.get(g.normalized_notation, "UNKNOWN"),
                "support_status": support.get(g.normalized_notation, {}).get(
                    "support_status", "UNKNOWN"
                ),
            }
            for g in groups[:30]
        ]
        unsupported = [
            {
                "notation": g.normalized_notation,
                "frequency": g.frequency,
                "category": categories.get(g.normalized_notation, "UNKNOWN"),
                "reason": support.get(g.normalized_notation, {}).get("support_reason", ""),
            }
            for g in groups
            if support.get(g.normalized_notation, {}).get("support_status") == "UNSUPPORTED"
        ]
        unsupported.sort(key=lambda x: -x["frequency"])
        return {
            "most_common": top,
            "most_common_unsupported": unsupported[:20],
            "total_unique": len(groups),
            "total_occurrences": sum(g.frequency for g in groups),
        }
