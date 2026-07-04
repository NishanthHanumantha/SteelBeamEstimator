"""Calculation index registry — Phase I.4.5."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from src.engineering_calculations.calculation_index.calculation_index_types import (
    NAMESPACE_CALCULATION_INDEX,
)


def format_calculation_index_id(sequence: int) -> str:
    return f"CALC_INDEX::{sequence:06d}"


def format_calculation_index_registry_id() -> str:
    return "CALC_INDEX_REGISTRY"


class CalculationIndexRegistry:
    """Deterministic registry with O(1) lookups for bar calculation indexes."""

    def __init__(self) -> None:
        self._sequence = 0
        self._indexes: dict[str, dict[str, Any]] = {}
        self._by_bar: dict[str, str] = {}
        self._by_category: dict[str, List[str]] = defaultdict(list)
        self._by_result: dict[str, List[str]] = defaultdict(list)

    def next_id(self) -> str:
        self._sequence += 1
        return format_calculation_index_id(self._sequence)

    def register(self, index: dict[str, Any]) -> str:
        index_id = str(index.get("index_id") or "")
        if not index_id:
            index_id = self.next_id()
            index = dict(index)
            index["index_id"] = index_id

        self._indexes[index_id] = index
        bar_id = str(index.get("bar_id", ""))
        if bar_id:
            self._by_bar[bar_id] = index_id

        references = index.get("references") or {}
        for category, result_id in references.items():
            if index_id not in self._by_category[str(category)]:
                self._by_category[str(category)].append(index_id)
            if index_id not in self._by_result[str(result_id)]:
                self._by_result[str(result_id)].append(index_id)

        return index_id

    def index(self, index_id: str) -> Optional[dict[str, Any]]:
        return self._indexes.get(index_id)

    def index_by_bar(self, bar_id: str) -> Optional[dict[str, Any]]:
        index_id = self._by_bar.get(str(bar_id))
        return self._indexes.get(index_id) if index_id else None

    def indexes_by_category(self, category: str) -> List[dict[str, Any]]:
        return self._collect(self._by_category.get(str(category), []))

    def indexes_by_result(self, result_id: str) -> List[dict[str, Any]]:
        return self._collect(self._by_result.get(str(result_id), []))

    def all_indexes(self) -> List[dict[str, Any]]:
        return list(self._indexes.values())

    @staticmethod
    def build_project_registry(
        indexes: List[dict[str, Any]],
        result_count: int,
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        category_counts: dict[str, int] = defaultdict(int)
        for index in indexes:
            for category in (index.get("references") or {}).keys():
                category_counts[str(category)] += 1

        return {
            "namespace": NAMESPACE_CALCULATION_INDEX,
            "phase": "Phase I.4.5",
            "registry_id": format_calculation_index_registry_id(),
            "index_count": len(indexes),
            "index_ids": [index.get("index_id") for index in indexes],
            "bar_count": len(indexes),
            "result_count": result_count,
            "category_counts": dict(sorted(category_counts.items())),
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
        }

    def _collect(self, index_ids: List[str]) -> List[dict[str, Any]]:
        return [self._indexes[index_id] for index_id in index_ids if index_id in self._indexes]
