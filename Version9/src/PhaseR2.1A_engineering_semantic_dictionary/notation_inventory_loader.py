"""Load Phase R.2.0.1 engineering notation inventory (read-only)."""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List, Optional

from .semantic_dictionary_models import InventoryItem


class NotationInventoryLoader:

    def __init__(
        self,
        inventory_path: pathlib.Path,
        priorities_path: Optional[pathlib.Path] = None,
    ):
        self._inventory_path = inventory_path
        self._priorities_path = priorities_path

    def load(self) -> List[InventoryItem]:
        if not self._inventory_path.exists():
            return []
        data = json.loads(self._inventory_path.read_text(encoding="utf-8"))
        priority_map = self._load_priorities()
        items = []
        for raw in data.get("items", []):
            notation = raw.get("normalized_notation") or raw.get("notation", "")
            impact = raw.get("impact", "LOW")
            if notation in priority_map:
                impact = priority_map[notation].get("impact", impact)
            items.append(InventoryItem(
                notation=raw.get("notation", notation),
                normalized_notation=notation,
                category=raw.get("category", "UNKNOWN"),
                frequency=int(raw.get("frequency", 0)),
                support_status=raw.get("support_status", "UNKNOWN"),
                support_reason=raw.get("support_reason", ""),
                example_text=raw.get("example_text", ""),
                beam_ids=list(raw.get("beam_ids", [])),
                drawing_ids=list(raw.get("drawing_ids", [])),
                entity_ids=list(raw.get("entity_ids", [])),
                impact=impact,
                recommendation=raw.get("recommendation", ""),
            ))
        return items

    def raw_json(self) -> Dict[str, Any]:
        if not self._inventory_path.exists():
            return {}
        return json.loads(self._inventory_path.read_text(encoding="utf-8"))

    def _load_priorities(self) -> Dict[str, Dict]:
        if not self._priorities_path or not self._priorities_path.exists():
            return {}
        data = json.loads(self._priorities_path.read_text(encoding="utf-8"))
        return {
            item["notation"]: item
            for item in data.get("items", [])
            if item.get("notation")
        }
