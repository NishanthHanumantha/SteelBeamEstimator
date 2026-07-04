"""Hook length registry — Phase I.4."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from src.engineering_calculations.hook_length_types import (
    NAMESPACE_HOOK_LENGTH,
    HookLengthState,
)


def format_hook_length_id(sequence: int) -> str:
    return f"HOOK_LENGTH::{sequence:06d}"


def format_hook_length_registry_id() -> str:
    return "HOOK_LENGTH_REGISTRY"


class HookLengthRegistry:
    """Sequence registry with O(1) lookups for hook length determinations."""

    def __init__(self) -> None:
        self._sequence = 0
        self._records: dict[str, dict[str, Any]] = {}
        self._by_result: dict[str, str] = {}
        self._by_bar: dict[str, str] = {}
        self._by_beam: dict[str, List[str]] = defaultdict(list)
        self._by_context: dict[str, List[str]] = defaultdict(list)
        self._by_diameter: dict[str, List[str]] = defaultdict(list)
        self._by_hook_angle: dict[str, List[str]] = defaultdict(list)
        self._by_hook_type: dict[str, List[str]] = defaultdict(list)
        self._by_hook_length: dict[str, List[str]] = defaultdict(list)
        self._by_state: dict[str, List[str]] = defaultdict(list)

    def next_id(self) -> str:
        self._sequence += 1
        return format_hook_length_id(self._sequence)

    def register(self, record: dict[str, Any]) -> str:
        record_id = str(record.get("hook_length_id") or "")
        if not record_id:
            record_id = self.next_id()
            record["hook_length_id"] = record_id

        self._records[record_id] = record

        result_id = str(record.get("result_id", ""))
        bar_id = str(record.get("bar_id", ""))
        beam_id = str(record.get("beam_id", ""))
        context_id = str(record.get("context_id", ""))
        diameter = str(record.get("bar_diameter_mm", ""))
        hook_angle = str(record.get("hook_angle", ""))
        hook_type = str(record.get("hook_type", ""))
        hook_length = record.get("hook_length_mm")
        state = str(record.get("determination_state", ""))

        if result_id:
            self._by_result[result_id] = record_id
        if bar_id:
            self._by_bar[bar_id] = record_id
        if beam_id and record_id not in self._by_beam[beam_id]:
            self._by_beam[beam_id].append(record_id)
        if context_id and record_id not in self._by_context[context_id]:
            self._by_context[context_id].append(record_id)
        if diameter and record_id not in self._by_diameter[diameter]:
            self._by_diameter[diameter].append(record_id)
        if hook_angle and record_id not in self._by_hook_angle[hook_angle]:
            self._by_hook_angle[hook_angle].append(record_id)
        if hook_type and record_id not in self._by_hook_type[hook_type]:
            self._by_hook_type[hook_type].append(record_id)
        if hook_length is not None and record_id not in self._by_hook_length[str(hook_length)]:
            self._by_hook_length[str(hook_length)].append(record_id)
        if state and record_id not in self._by_state[state]:
            self._by_state[state].append(record_id)

        return record_id

    def record(self, hook_length_id: str) -> Optional[dict[str, Any]]:
        return self._records.get(hook_length_id)

    def record_by_result(self, result_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_result.get(result_id)
        return self._records.get(record_id) if record_id else None

    def record_by_bar(self, bar_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_bar.get(bar_id)
        return self._records.get(record_id) if record_id else None

    def records_by_beam(self, beam_id: str) -> List[dict[str, Any]]:
        return self._collect(self._by_beam.get(beam_id, []))

    def records_by_context(self, context_id: str) -> List[dict[str, Any]]:
        return self._collect(self._by_context.get(context_id, []))

    def records_by_diameter(self, diameter_mm: int | str) -> List[dict[str, Any]]:
        return self._collect(self._by_diameter.get(str(diameter_mm), []))

    def records_by_hook_angle(self, hook_angle: int | str) -> List[dict[str, Any]]:
        return self._collect(self._by_hook_angle.get(str(hook_angle), []))

    def records_by_hook_type(self, hook_type: str) -> List[dict[str, Any]]:
        return self._collect(self._by_hook_type.get(str(hook_type), []))

    def records_by_hook_length(self, hook_length_mm: int | float) -> List[dict[str, Any]]:
        return self._collect(self._by_hook_length.get(str(hook_length_mm), []))

    def records_by_state(self, state: str) -> List[dict[str, Any]]:
        return self._collect(self._by_state.get(state, []))

    def all_records(self) -> List[dict[str, Any]]:
        return list(self._records.values())

    @staticmethod
    def build_project_registry(
        records: List[dict[str, Any]],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        by_state: dict[str, int] = defaultdict(int)
        by_beam: dict[str, int] = defaultdict(int)
        by_angle: dict[str, int] = defaultdict(int)
        by_type: dict[str, int] = defaultdict(int)
        by_source: dict[str, int] = defaultdict(int)

        for record in records:
            state = str(record.get("determination_state", HookLengthState.DEFERRED.value))
            by_state[state] += 1
            beam_id = str(record.get("beam_id", ""))
            if beam_id:
                by_beam[beam_id] += 1
            angle = str(record.get("hook_angle", ""))
            if angle:
                by_angle[angle] += 1
            hook_type = str(record.get("hook_type", ""))
            if hook_type:
                by_type[hook_type] += 1
            source = str(record.get("hook_rule_source", ""))
            if source:
                by_source[source] += 1

        state_counts = {
            "calculated": by_state.get(HookLengthState.CALCULATED.value, 0),
            "deferred": by_state.get(HookLengthState.DEFERRED.value, 0),
            "blocked": by_state.get(HookLengthState.BLOCKED.value, 0),
            "failed": by_state.get(HookLengthState.FAILED.value, 0),
        }

        return {
            "namespace": NAMESPACE_HOOK_LENGTH,
            "phase": "Phase I.4",
            "registry_id": format_hook_length_registry_id(),
            "determination_count": len(records),
            "determination_ids": [record.get("hook_length_id") for record in records],
            "results_by_state": dict(by_state),
            "state_counts": state_counts,
            "results_by_beam": dict(by_beam),
            "results_by_hook_angle": dict(by_angle),
            "results_by_hook_type": dict(by_type),
            "results_by_rule_source": dict(by_source),
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
        }

    def _collect(self, record_ids: List[str]) -> List[dict[str, Any]]:
        return [self._records[record_id] for record_id in record_ids if record_id in self._records]
