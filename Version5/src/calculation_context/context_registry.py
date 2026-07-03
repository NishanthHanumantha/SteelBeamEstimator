"""Calculation context registry — Phase I.1."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from src.calculation_context.calculation_context_types import NAMESPACE_CALCULATION_CONTEXT


def format_calculation_context_id(sequence: int) -> str:
    return f"CALC_CTX::{sequence:06d}"


def format_calculation_context_registry_id() -> str:
    return "CALC_CTX_REGISTRY"


class CalculationContextRegistry:
    """Sequence registry with O(1) lookups for calculation contexts."""

    def __init__(self) -> None:
        self._sequence = 0
        self._contexts: dict[str, dict[str, Any]] = {}
        self._by_specification: dict[str, str] = {}
        self._by_association: dict[str, str] = {}
        self._by_engineering_object: dict[str, str] = {}
        self._by_beam: dict[str, List[str]] = defaultdict(list)
        self._processed_specification_ids: List[str] = []

    def next_id(self) -> str:
        self._sequence += 1
        return format_calculation_context_id(self._sequence)

    def register(self, context: dict[str, Any]) -> str:
        context_id = str(context.get("context_id") or "")
        if not context_id:
            context_id = self.next_id()
            context["context_id"] = context_id

        self._contexts[context_id] = context

        spec_id = str(context.get("specification_id", ""))
        assoc_id = str(context.get("association_id", ""))
        object_id = str(context.get("engineering_object_id", ""))
        beam_id = str(context.get("beam_id", ""))

        if spec_id:
            self._by_specification[spec_id] = context_id
        if assoc_id:
            self._by_association[assoc_id] = context_id
        if object_id:
            self._by_engineering_object[object_id] = context_id
        if beam_id:
            if context_id not in self._by_beam[beam_id]:
                self._by_beam[beam_id].append(context_id)

        return context_id

    def mark_processed(self, specification_id: str) -> None:
        if specification_id and specification_id not in self._processed_specification_ids:
            self._processed_specification_ids.append(specification_id)

    def context(self, context_id: str) -> Optional[dict[str, Any]]:
        return self._contexts.get(context_id)

    def context_by_specification(self, specification_id: str) -> Optional[dict[str, Any]]:
        context_id = self._by_specification.get(specification_id)
        return self._contexts.get(context_id) if context_id else None

    def context_by_association(self, association_id: str) -> Optional[dict[str, Any]]:
        context_id = self._by_association.get(association_id)
        return self._contexts.get(context_id) if context_id else None

    def context_by_engineering_object(
        self,
        engineering_object_id: str,
    ) -> Optional[dict[str, Any]]:
        context_id = self._by_engineering_object.get(engineering_object_id)
        return self._contexts.get(context_id) if context_id else None

    def contexts_by_beam(self, beam_id: str) -> List[dict[str, Any]]:
        return [
            self._contexts[context_id]
            for context_id in self._by_beam.get(beam_id, [])
            if context_id in self._contexts
        ]

    def all_contexts(self) -> List[dict[str, Any]]:
        return list(self._contexts.values())

    @property
    def processed_specification_ids(self) -> List[str]:
        return list(self._processed_specification_ids)

    @staticmethod
    def build_project_registry(
        contexts: List[dict[str, Any]],
        specifications: List[dict[str, Any]],
        processed_specification_ids: List[str],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        by_status: Dict[str, int] = {}
        by_beam: Dict[str, int] = {}
        for context in contexts:
            status = str(context.get("calculation_status", "UNKNOWN"))
            by_status[status] = by_status.get(status, 0) + 1
            beam = str(context.get("beam_id", ""))
            if beam:
                by_beam[beam] = by_beam.get(beam, 0) + 1

        return {
            "namespace": NAMESPACE_CALCULATION_CONTEXT,
            "phase": "Phase I.1",
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
            "registry_id": format_calculation_context_registry_id(),
            "context_count": len(contexts),
            "context_ids": [item.get("context_id") for item in contexts],
            "specification_count": len(specifications),
            "processed_specification_ids": list(processed_specification_ids),
            "contexts_by_status": by_status,
            "contexts_by_beam": by_beam,
        }
