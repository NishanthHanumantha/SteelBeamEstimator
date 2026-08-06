"""STEP 8 — Coverage and readiness statistics."""
from __future__ import annotations

from typing import Any, Dict, List

from .notation_models import PriorityItem, RawTextEntity, VocabularyEntry


class NotationStatistics:

    def compute(
        self,
        entities: List[RawTextEntity],
        entries: List[VocabularyEntry],
        priorities: List[PriorityItem],
        category_dist: Dict[str, Any],
        frequency: Dict[str, Any],
        symbols: Dict[str, Any],
    ) -> Dict[str, Any]:
        total_unique = len(entries)
        by_status: Dict[str, int] = {}
        for e in entries:
            by_status[e.support_status] = by_status.get(e.support_status, 0) + 1

        def pct(n: int) -> float:
            return round(100.0 * n / total_unique, 2) if total_unique else 0.0

        entity_counts: Dict[str, int] = {}
        for ent in entities:
            entity_counts[ent.entity_type] = entity_counts.get(ent.entity_type, 0) + 1

        return {
            "model_version": "7.9.1",
            "total_dxf_entities": len(entities),
            "entity_type_counts": entity_counts,
            "total_unique_notations": total_unique,
            "total_occurrences": frequency.get("total_occurrences", 0),
            "support_distribution": by_status,
            "supported_pct": pct(by_status.get("SUPPORTED", 0)),
            "partially_supported_pct": pct(by_status.get("PARTIALLY_SUPPORTED", 0)),
            "unsupported_pct": pct(by_status.get("UNSUPPORTED", 0)),
            "unknown_pct": pct(by_status.get("UNKNOWN", 0)),
            "category_distribution": category_dist,
            "engineering_symbols_discovered": symbols.get("symbol_count", 0),
            "symbol_families": symbols.get("families_discovered", []),
            "priority_count": len(priorities),
            "most_common": frequency.get("most_common", [])[:15],
            "most_common_unsupported": frequency.get("most_common_unsupported", [])[:15],
        }
