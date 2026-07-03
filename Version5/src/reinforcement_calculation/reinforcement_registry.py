"""Reinforcement calculation registry — Phase I.2."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from src.reinforcement_calculation.calculation_state import CalculationState, parse_calculation_state
from src.reinforcement_calculation.reinforcement_types import NAMESPACE_REBAR


def format_rebar_id(sequence: int) -> str:
    return f"REBAR::{sequence:06d}"


def format_rebar_group_id(sequence: int) -> str:
    return f"REBAR_GROUP::{sequence:06d}"


def format_rebar_registry_id() -> str:
    return "REBAR_REGISTRY"


class ReinforcementRegistry:
    """Sequence registry with O(1) lookups for reinforcement bars and groups."""

    def __init__(self) -> None:
        self._bar_sequence = 0
        self._group_sequence = 0
        self._bars: dict[str, dict[str, Any]] = {}
        self._groups: dict[str, dict[str, Any]] = {}
        self._by_context: dict[str, str] = {}
        self._by_specification: dict[str, str] = {}
        self._by_beam: dict[str, List[str]] = defaultdict(list)
        self._by_role: dict[str, List[str]] = defaultdict(list)
        self._by_diameter: dict[int, List[str]] = defaultdict(list)
        self._group_by_context: dict[str, str] = {}
        self._group_by_specification: dict[str, str] = {}
        self._by_bar_state: dict[str, List[str]] = defaultdict(list)
        self._by_group_state: dict[str, List[str]] = defaultdict(list)
        self._processed_context_ids: List[str] = []

    def next_bar_id(self) -> str:
        self._bar_sequence += 1
        return format_rebar_id(self._bar_sequence)

    def next_group_id(self) -> str:
        self._group_sequence += 1
        return format_rebar_group_id(self._group_sequence)

    def register_bar(self, bar: dict[str, Any]) -> str:
        bar_id = str(bar.get("bar_id") or "")
        if not bar_id:
            bar_id = self.next_bar_id()
            bar["bar_id"] = bar_id

        self._bars[bar_id] = bar

        context_id = str(bar.get("context_id", ""))
        spec_id = str(bar.get("specification_id", ""))
        beam_id = str(bar.get("beam_id", ""))
        role = str(bar.get("role", ""))
        diameter = bar.get("diameter_mm")

        if context_id:
            self._by_context[context_id] = bar_id
        if spec_id:
            self._by_specification[spec_id] = bar_id
        if beam_id and bar_id not in self._by_beam[beam_id]:
            self._by_beam[beam_id].append(bar_id)
        if role and bar_id not in self._by_role[role]:
            self._by_role[role].append(bar_id)
        if diameter is not None:
            diameter_key = int(float(diameter))
            if bar_id not in self._by_diameter[diameter_key]:
                self._by_diameter[diameter_key].append(bar_id)

        state = self._readiness_state(bar)
        if bar_id not in self._by_bar_state[state]:
            self._by_bar_state[state].append(bar_id)

        return bar_id

    def register_group(self, group: dict[str, Any]) -> str:
        group_id = str(group.get("group_id") or "")
        if not group_id:
            group_id = self.next_group_id()
            group["group_id"] = group_id

        self._groups[group_id] = group

        context_id = str(group.get("context_id", ""))
        spec_id = str(group.get("specification_id", ""))
        if context_id:
            self._group_by_context[context_id] = group_id
        if spec_id:
            self._group_by_specification[spec_id] = group_id

        state = self._readiness_state(group)
        if group_id not in self._by_group_state[state]:
            self._by_group_state[state].append(group_id)

        return group_id

    @staticmethod
    def _readiness_state(record: dict[str, Any]) -> str:
        readiness = record.get("calculation_readiness", {})
        return str(readiness.get("calculation_state", CalculationState.UNKNOWN.value))

    def mark_processed(self, context_id: str) -> None:
        if context_id and context_id not in self._processed_context_ids:
            self._processed_context_ids.append(context_id)

    def bar(self, bar_id: str) -> Optional[dict[str, Any]]:
        return self._bars.get(bar_id)

    def group(self, group_id: str) -> Optional[dict[str, Any]]:
        return self._groups.get(group_id)

    def bar_by_context(self, context_id: str) -> Optional[dict[str, Any]]:
        bar_id = self._by_context.get(context_id)
        return self._bars.get(bar_id) if bar_id else None

    def bar_by_specification(self, specification_id: str) -> Optional[dict[str, Any]]:
        bar_id = self._by_specification.get(specification_id)
        return self._bars.get(bar_id) if bar_id else None

    def bars_by_beam(self, beam_id: str) -> List[dict[str, Any]]:
        return [
            self._bars[bar_id]
            for bar_id in self._by_beam.get(beam_id, [])
            if bar_id in self._bars
        ]

    def bars_by_role(self, role: str) -> List[dict[str, Any]]:
        return [
            self._bars[bar_id]
            for bar_id in self._by_role.get(role, [])
            if bar_id in self._bars
        ]

    def bars_by_diameter(self, diameter_mm: int) -> List[dict[str, Any]]:
        return [
            self._bars[bar_id]
            for bar_id in self._by_diameter.get(int(diameter_mm), [])
            if bar_id in self._bars
        ]

    def group_by_context(self, context_id: str) -> Optional[dict[str, Any]]:
        group_id = self._group_by_context.get(context_id)
        return self._groups.get(group_id) if group_id else None

    def group_by_specification(self, specification_id: str) -> Optional[dict[str, Any]]:
        group_id = self._group_by_specification.get(specification_id)
        return self._groups.get(group_id) if group_id else None

    def get_ready_bars(self) -> List[dict[str, Any]]:
        return self._bars_by_state(CalculationState.READY.value)

    def get_deferred_bars(self) -> List[dict[str, Any]]:
        return self._bars_by_state(CalculationState.DEFERRED.value)

    def get_blocked_bars(self) -> List[dict[str, Any]]:
        return self._bars_by_state(CalculationState.BLOCKED.value)

    def get_ready_groups(self) -> List[dict[str, Any]]:
        return self._groups_by_state(CalculationState.READY.value)

    def get_deferred_groups(self) -> List[dict[str, Any]]:
        return self._groups_by_state(CalculationState.DEFERRED.value)

    def get_blocked_groups(self) -> List[dict[str, Any]]:
        return self._groups_by_state(CalculationState.BLOCKED.value)

    def _bars_by_state(self, state: str) -> List[dict[str, Any]]:
        return [
            self._bars[bar_id]
            for bar_id in self._by_bar_state.get(state, [])
            if bar_id in self._bars
        ]

    def _groups_by_state(self, state: str) -> List[dict[str, Any]]:
        return [
            self._groups[group_id]
            for group_id in self._by_group_state.get(state, [])
            if group_id in self._groups
        ]

    def all_bars(self) -> List[dict[str, Any]]:
        return list(self._bars.values())

    def all_groups(self) -> List[dict[str, Any]]:
        return list(self._groups.values())

    @property
    def processed_context_ids(self) -> List[str]:
        return list(self._processed_context_ids)

    @staticmethod
    def build_project_registry(
        bars: List[dict[str, Any]],
        groups: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
        processed_context_ids: List[str],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        by_role: Dict[str, int] = {}
        by_diameter: Dict[str, int] = {}
        by_beam: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        by_readiness: Dict[str, int] = {}

        for bar in bars:
            role = str(bar.get("role", "UNKNOWN"))
            by_role[role] = by_role.get(role, 0) + 1
            diameter = bar.get("diameter_mm")
            if diameter is not None:
                key = str(int(float(diameter)))
                by_diameter[key] = by_diameter.get(key, 0) + 1
            beam = str(bar.get("beam_id", ""))
            if beam:
                by_beam[beam] = by_beam.get(beam, 0) + 1
            readiness = parse_calculation_state(
                (bar.get("calculation_readiness") or {}).get("calculation_state")
            )
            by_readiness[readiness.value] = by_readiness.get(readiness.value, 0) + 1

        for group in groups:
            status = str(group.get("status", "UNKNOWN"))
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "namespace": NAMESPACE_REBAR,
            "phase": "Phase I.2",
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
            "registry_id": format_rebar_registry_id(),
            "bar_count": len(bars),
            "group_count": len(groups),
            "bar_ids": [item.get("bar_id") for item in bars],
            "group_ids": [item.get("group_id") for item in groups],
            "context_count": len(contexts),
            "processed_context_ids": list(processed_context_ids),
            "bars_by_role": by_role,
            "bars_by_diameter": by_diameter,
            "bars_by_beam": by_beam,
            "groups_by_status": by_status,
            "bars_by_readiness": by_readiness,
            "readiness_counts": {
                "ready": by_readiness.get(CalculationState.READY.value, 0),
                "deferred": by_readiness.get(CalculationState.DEFERRED.value, 0),
                "blocked": by_readiness.get(CalculationState.BLOCKED.value, 0),
            },
        }
