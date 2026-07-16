"""Coverage and distribution statistics for the semantic dictionary."""
from __future__ import annotations

from typing import Any, Dict

from .semantic_dictionary_loader import SemanticDictionaryLoader
from .semantic_dictionary_models import SemanticDictionary


class SemanticDictionaryStatistics:

    def compute(
        self, dictionary: SemanticDictionary, loader: SemanticDictionaryLoader
    ) -> Dict[str, Any]:
        base = loader.statistics()
        entries = list(dictionary.entries.values())
        high = [e for e in entries if e.priority == "HIGH"]
        unsupported_mapped = [
            e for e in entries
            if e.support_status == "UNSUPPORTED" and e.engineering_meaning != "UNKNOWN"
        ]
        return {
            "model_version": dictionary.version.model_version,
            "dictionary_version": dictionary.version.dictionary_version,
            "unique_entries": base["entry_count"],
            "categories": base["categories"],
            "supported": dictionary.version.supported_count,
            "unsupported": dictionary.version.unsupported_count,
            "unknown": dictionary.version.unknown_count,
            "priority_distribution": base["priorities"],
            "meaning_distribution": base["meanings"],
            "role_distribution": base["roles"],
            "position_distribution": base["positions"],
            "coverage_pct": base["coverage_pct"],
            "vocabulary_completeness_pct": base["vocabulary_completeness_pct"],
            "vocabulary_aliases": base["vocabulary_aliases"],
            "high_priority_entries": len(high),
            "unsupported_with_meaning": len(unsupported_mapped),
            "inventory_hash": dictionary.version.inventory_hash,
            "ready_for_r21b": len(unsupported_mapped) > 0,
        }
