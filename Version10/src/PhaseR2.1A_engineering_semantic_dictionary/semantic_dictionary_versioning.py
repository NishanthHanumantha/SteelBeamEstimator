"""Dictionary version metadata and inventory hash."""
from __future__ import annotations

import hashlib
import pathlib
from datetime import datetime
from typing import Any, Dict

from .semantic_dictionary_models import DictionaryEntry, DictionaryVersion


class SemanticDictionaryVersioning:

    def __init__(self, config: Dict[str, Any]):
        self._config = config

    def build(
        self,
        entries: Dict[str, DictionaryEntry],
        inventory_path: pathlib.Path,
    ) -> DictionaryVersion:
        supported = sum(1 for e in entries.values() if e.support_status == "SUPPORTED")
        unsupported = sum(
            1 for e in entries.values() if e.support_status == "UNSUPPORTED"
        )
        unknown = sum(1 for e in entries.values() if e.support_status == "UNKNOWN")
        partial = sum(
            1 for e in entries.values() if e.support_status == "PARTIALLY_SUPPORTED"
        )
        return DictionaryVersion(
            model_version=str(self._config.get("model_version", "7.10.0")),
            dictionary_version=str(self._config.get("dictionary_version", "1.0.0")),
            created_time=datetime.utcnow().isoformat() + "Z",
            generated_from=str(self._config.get("source", "R2.0.1_INVENTORY")),
            inventory_hash=self._hash_file(inventory_path),
            entry_count=len(entries),
            supported_count=supported,
            unsupported_count=unsupported,
            unknown_count=unknown,
            partially_supported_count=partial,
        )

    @staticmethod
    def _hash_file(path: pathlib.Path) -> str:
        if not path.exists():
            return "MISSING"
        h = hashlib.sha256()
        h.update(path.read_bytes())
        return h.hexdigest()[:16]
