"""Build Engineering Semantic Dictionary from R.2.0.1 inventory + YAML vocabulary."""
from __future__ import annotations

from typing import Any, Dict, List

from .engineering_vocabulary_resolver import EngineeringVocabularyResolver
from .semantic_dictionary_models import DictionaryEntry, InventoryItem


class SemanticDictionaryBuilder:

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self._resolver = EngineeringVocabularyResolver(config)
        self._source = config.get("source", "R2.0.1_INVENTORY")
        self._future = config.get("future_phase_default", "R.2.1B")
        self._defaults = config.get("defaults", {})

    def build(self, inventory: List[InventoryItem]) -> Dict[str, DictionaryEntry]:
        entries: Dict[str, DictionaryEntry] = {}
        for item in inventory:
            key = item.normalized_notation
            if key in entries:
                # Merge frequency / examples for duplicate keys
                existing = entries[key]
                existing.frequency += item.frequency
                if item.example_text and item.example_text not in existing.examples:
                    existing.examples.append(item.example_text)
                continue
            entries[key] = self._build_entry(item)
        return entries

    def _build_entry(self, item: InventoryItem) -> DictionaryEntry:
        meaning, meta = self._resolver.resolve_full(
            item.normalized_notation, item.category
        )
        category = meta.get("category") or item.category or "UNKNOWN"
        priority = item.impact if item.impact and item.impact != "NONE" else (
            meta.get("priority") or self._defaults.get("priority", "LOW")
        )
        if item.support_status == "SUPPORTED" and priority in ("HIGH", "MEDIUM"):
            # Supported bar callouts stay LOW priority for R.2.1B
            if meaning in ("TOP_MAIN", "BOTTOM_MAIN", "STIRRUP"):
                priority = "LOW"

        confidence = "HIGH" if meaning != "UNKNOWN" else "MEDIUM"
        if item.support_status == "UNSUPPORTED" and meaning != "UNKNOWN":
            confidence = "HIGH"
        if meaning == "UNKNOWN":
            confidence = "LOW"

        aliases = list(meta.get("aliases", []))
        examples = [item.example_text] if item.example_text else []
        if item.notation not in examples:
            examples.insert(0, item.notation)

        return DictionaryEntry(
            notation=item.notation,
            normalized_notation=item.normalized_notation,
            category=category,
            engineering_meaning=meaning,
            engineering_role=meta.get("engineering_role"),
            position=meta.get("position"),
            quantity_multiplier=float(meta.get("quantity_multiplier", 1) or 1),
            support_status=item.support_status,
            priority=str(priority),
            confidence=confidence,
            description=meta.get("description") or item.recommendation
            or self._defaults.get("description", ""),
            examples=[e for e in examples if e][:5],
            future_phase=meta.get("future_phase") or self._future,
            source=self._source,
            frequency=item.frequency,
            aliases=aliases,
        )

    @property
    def resolver(self) -> EngineeringVocabularyResolver:
        return self._resolver
