"""SemanticDictionaryLoader API — consumed by future semantic phases."""
from __future__ import annotations

import pathlib
from typing import Any, Dict, List, Optional

import yaml

from .notation_inventory_loader import NotationInventoryLoader
from .semantic_dictionary_builder import SemanticDictionaryBuilder
from .semantic_dictionary_cache import SemanticDictionaryCache
from .semantic_dictionary_models import DictionaryEntry, SemanticDictionary
from .semantic_dictionary_versioning import SemanticDictionaryVersioning


class SemanticDictionaryLoader:
    """
    Public API for Engineering Semantic Dictionary.

    Methods: load, reload, get, contains, all_entries,
    find_by_category, find_by_role, find_by_meaning,
    find_by_priority, statistics.
    """

    def __init__(
        self,
        v7_root: pathlib.Path,
        config_path: Optional[pathlib.Path] = None,
    ):
        self._v7 = v7_root
        self._config_path = config_path or (
            v7_root / "config" / "engineering_semantic_dictionary.yaml"
        )
        self._config: Dict[str, Any] = {}
        self._dictionary: Optional[SemanticDictionary] = None

    def load(self) -> SemanticDictionary:
        cached = SemanticDictionaryCache.get()
        if cached is not None:
            self._dictionary = cached
            return cached
        return self.reload()

    def reload(self) -> SemanticDictionary:
        self._config = self._read_config()
        paths = self._config.get("paths", {})
        inv_path = self._v7 / paths.get(
            "inventory",
            "data/output/PhaseR2.0.1_engineering_notation_inventory/"
            "engineering_notation_inventory.json",
        )
        pri_path = self._v7 / paths.get(
            "priorities",
            "data/output/PhaseR2.0.1_engineering_notation_inventory/"
            "implementation_priority.json",
        )
        inventory = NotationInventoryLoader(inv_path, pri_path).load()
        builder = SemanticDictionaryBuilder(self._config)
        entries = builder.build(inventory)
        version = SemanticDictionaryVersioning(self._config).build(
            entries, inv_path
        )
        dictionary = SemanticDictionary(
            version=version,
            entries=entries,
            vocabulary_map=builder.resolver.vocabulary_map(),
        )
        SemanticDictionaryCache.set(dictionary)
        self._dictionary = dictionary
        return dictionary

    def get(self, notation: str) -> Optional[DictionaryEntry]:
        d = self._ensure()
        if notation in d.entries:
            return d.entries[notation]
        # Try normalized lookup
        for key, entry in d.entries.items():
            if key.upper() == notation.upper() or entry.notation.upper() == notation.upper():
                return entry
        return None

    def contains(self, notation: str) -> bool:
        return self.get(notation) is not None

    def all_entries(self) -> List[DictionaryEntry]:
        d = self._ensure()
        return list(d.entries.values())

    def find_by_category(self, category: str) -> List[DictionaryEntry]:
        return [e for e in self.all_entries() if e.category == category]

    def find_by_role(self, role: str) -> List[DictionaryEntry]:
        return [e for e in self.all_entries() if e.engineering_role == role]

    def find_by_meaning(self, meaning: str) -> List[DictionaryEntry]:
        return [e for e in self.all_entries() if e.engineering_meaning == meaning]

    def find_by_priority(self, priority: str) -> List[DictionaryEntry]:
        return [e for e in self.all_entries() if e.priority == priority]

    def statistics(self) -> Dict[str, Any]:
        d = self._ensure()
        entries = list(d.entries.values())
        by_cat: Dict[str, int] = {}
        by_meaning: Dict[str, int] = {}
        by_role: Dict[str, int] = {}
        by_pos: Dict[str, int] = {}
        by_pri: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        for e in entries:
            by_cat[e.category] = by_cat.get(e.category, 0) + 1
            by_meaning[e.engineering_meaning] = by_meaning.get(e.engineering_meaning, 0) + 1
            if e.engineering_role:
                by_role[e.engineering_role] = by_role.get(e.engineering_role, 0) + 1
            if e.position:
                by_pos[e.position] = by_pos.get(e.position, 0) + 1
            by_pri[e.priority] = by_pri.get(e.priority, 0) + 1
            by_status[e.support_status] = by_status.get(e.support_status, 0) + 1
        total = len(entries) or 1
        mapped = sum(1 for e in entries if e.engineering_meaning != "UNKNOWN")
        return {
            "entry_count": len(entries),
            "categories": by_cat,
            "meanings": by_meaning,
            "roles": by_role,
            "positions": by_pos,
            "priorities": by_pri,
            "support_status": by_status,
            "vocabulary_aliases": len(d.vocabulary_map),
            "coverage_pct": round(100.0 * mapped / total, 2),
            "vocabulary_completeness_pct": round(100.0 * mapped / total, 2),
            "version": d.version.to_dict(),
        }

    def dictionary(self) -> SemanticDictionary:
        return self._ensure()

    def _ensure(self) -> SemanticDictionary:
        if self._dictionary is None:
            return self.load()
        return self._dictionary

    def _read_config(self) -> Dict[str, Any]:
        if not self._config_path.exists():
            return {}
        return yaml.safe_load(self._config_path.read_text(encoding="utf-8")) or {}
