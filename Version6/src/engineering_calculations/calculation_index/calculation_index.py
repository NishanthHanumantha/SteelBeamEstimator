"""Calculation index object — Phase I.4.5."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.engineering_calculations.calculation_index.calculation_index_types import (
    CREATED_PHASE,
    SUPPORTED_INDEX_CATEGORIES,
)


class CalculationIndex:
    """Immutable reference-only index of engineering calculation results for one bar."""

    def __init__(
        self,
        index_id: str,
        bar_id: str,
        references: dict[str, str],
    ) -> None:
        self._index_id = str(index_id)
        self._bar_id = str(bar_id)
        self._references = {
            str(category): str(result_id)
            for category, result_id in sorted(references.items())
            if category in SUPPORTED_INDEX_CATEGORIES and result_id
        }

    @property
    def index_id(self) -> str:
        return self._index_id

    @property
    def bar_id(self) -> str:
        return self._bar_id

    def get(self, category: str) -> Optional[str]:
        return self._references.get(str(category))

    def has(self, category: str) -> bool:
        return str(category) in self._references

    def add(self, category: str, result_id: str) -> "CalculationIndex":
        updated = dict(self._references)
        updated[str(category)] = str(result_id)
        return CalculationIndex(self._index_id, self._bar_id, updated)

    def remove(self, category: str) -> "CalculationIndex":
        updated = dict(self._references)
        updated.pop(str(category), None)
        return CalculationIndex(self._index_id, self._bar_id, updated)

    def replace(self, category: str, result_id: str) -> "CalculationIndex":
        return self.add(category, result_id)

    def get_by_category(self, category: str) -> Optional[str]:
        return self.get(category)

    def list_categories(self) -> List[str]:
        return sorted(self._references.keys())

    def list_results(self) -> List[str]:
        return [self._references[category] for category in self.list_categories()]

    def count(self) -> int:
        return len(self._references)

    def to_dict(self) -> dict[str, Any]:
        categories = self.list_categories()
        return {
            "index_id": self._index_id,
            "bar_id": self._bar_id,
            "references": {category: self._references[category] for category in categories},
            "categories": categories,
            "reference_count": self.count(),
            "metadata": {
                "created_phase": CREATED_PHASE,
                "reference_only": True,
            },
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CalculationIndex":
        references = payload.get("references") or {}
        return cls(
            str(payload.get("index_id", "")),
            str(payload.get("bar_id", "")),
            dict(references),
        )
