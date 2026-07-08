"""Analyze leader ownership for duplicate members."""

from __future__ import annotations

from typing import Any, Dict, List


class LeaderAnalysis:
    """Analyze leader and association ownership differences."""

    def analyze(self, contexts: List[dict[str, Any]]) -> dict[str, Any]:
        leaders = [str(item.get("leader") or "NONE") for item in contexts]
        association_sources = [str(item.get("association_source") or "UNKNOWN") for item in contexts]
        unique_leaders = sorted(set(leaders))
        unique_sources = sorted(set(association_sources))
        return {
            "leaders": leaders,
            "unique_leaders": unique_leaders,
            "leader_variant": len(unique_leaders) > 1 and "NONE" not in unique_leaders,
            "association_sources": association_sources,
            "unique_association_sources": unique_sources,
            "association_variant": len(unique_sources) > 1,
        }
