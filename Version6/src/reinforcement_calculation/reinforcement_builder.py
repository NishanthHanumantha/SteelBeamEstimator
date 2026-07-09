"""Reinforcement Builder — Phase I.2."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from src.reinforcement_calculation.readiness_evaluator import CalculationReadinessEvaluator
from src.reinforcement_calculation.reinforcement_models import (
    build_reinforcement_bar,
    build_reinforcement_group,
)
from src.reinforcement_calculation.reinforcement_registry import ReinforcementRegistry
from src.reinforcement_calculation.reinforcement_types import (
    ROLE_TO_BAR_TYPE,
    ROLE_TO_POSITION,
    ROLE_UNKNOWN,
    SPECIFICATION_TYPE_TO_ROLE,
    STATUS_INCOMPLETE,
    STATUS_NORMALIZED,
    STATUS_PARTIAL,
)


class ReinforcementBuilder:
    """Normalize engineering specifications into reinforcement bar objects."""

    def __init__(self) -> None:
        self._readiness_evaluator = CalculationReadinessEvaluator()

    def build(
        self,
        specifications: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
    ) -> Tuple[List[dict[str, Any]], List[dict[str, Any]], ReinforcementRegistry]:
        registry = ReinforcementRegistry()
        context_by_spec = {
            str(item.get("specification_id", "")): item for item in contexts
        }

        bars: List[dict[str, Any]] = []
        groups: List[dict[str, Any]] = []

        sorted_specs = sorted(
            specifications,
            key=lambda item: str(item.get("specification_id", "")),
        )

        for spec in sorted_specs:
            spec_id = str(spec.get("specification_id", ""))
            context = context_by_spec.get(spec_id, {})
            context_id = str(context.get("context_id", ""))
            registry.mark_processed(context_id)

            bar, group = self._normalize_specification(spec, context, registry)
            registry.register_bar(bar)
            registry.register_group(group)
            bars.append(bar)
            groups.append(group)

        return bars, groups, registry

    @staticmethod
    def build_project_exports(
        bars: List[dict[str, Any]],
        groups: List[dict[str, Any]],
        registry: ReinforcementRegistry,
        contexts: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]],
        project_id: str = "",
    ) -> dict[str, Any]:
        primary = drawing_models[0] if drawing_models else {}
        reinforcement_registry = ReinforcementRegistry.build_project_registry(
            bars,
            groups,
            contexts,
            registry.processed_context_ids,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )
        return {
            "reinforcement_bars": bars,
            "reinforcement_groups": groups,
            "reinforcement_registry": reinforcement_registry,
        }

    def _normalize_specification(
        self,
        spec: dict[str, Any],
        context: dict[str, Any],
        registry: ReinforcementRegistry,
    ) -> Tuple[dict[str, Any], dict[str, Any]]:
        specification_id = str(spec.get("specification_id", ""))
        context_id = str(context.get("context_id", ""))
        beam_id = str(spec.get("beam_id", "") or context.get("beam_id", ""))
        reinforcement_type = str(spec.get("reinforcement_type", "UNKNOWN"))

        role = self._resolve_role(reinforcement_type)
        bar_type = ROLE_TO_BAR_TYPE.get(role, ROLE_TO_BAR_TYPE[ROLE_UNKNOWN])
        position = self._resolve_position(spec, role)
        quantity = _parse_quantity(spec.get("quantity"))
        diameter_mm = _parse_diameter_mm(spec.get("diameter"))
        steel_grade = context.get("steel_grade")
        orientation = context.get("beam_orientation")
        layer = spec.get("level")
        shape = spec.get("shape_code")
        continuity = self._resolve_continuity(spec)
        bar_status = self._resolve_bar_status(quantity, diameter_mm, role, steel_grade)
        group_status = bar_status

        traceability = self._build_traceability(spec, context)

        bar_id = registry.next_bar_id()
        group_id = registry.next_group_id()

        provisional_bar = build_reinforcement_bar(
            bar_id=bar_id,
            beam_id=beam_id,
            context_id=context_id,
            specification_id=specification_id,
            bar_mark=spec.get("bar_mark"),
            role=role,
            position=position,
            quantity=quantity,
            diameter_mm=diameter_mm,
            steel_grade=steel_grade,
            bar_type=bar_type,
            continuity=continuity,
            orientation=orientation,
            layer=layer,
            shape=shape,
            status=bar_status,
            traceability=traceability,
        )
        provisional_group = build_reinforcement_group(
            group_id=group_id,
            beam_id=beam_id,
            context_id=context_id,
            specification_id=specification_id,
            bars=[provisional_bar],
            group_type=reinforcement_type,
            engineering_role=role,
            status=group_status,
            traceability=traceability,
        )

        readiness = self._readiness_evaluator.evaluate(
            context,
            provisional_group,
            provisional_bar,
        )

        bar = build_reinforcement_bar(
            bar_id=bar_id,
            beam_id=beam_id,
            context_id=context_id,
            specification_id=specification_id,
            bar_mark=spec.get("bar_mark"),
            role=role,
            position=position,
            quantity=quantity,
            diameter_mm=diameter_mm,
            steel_grade=steel_grade,
            bar_type=bar_type,
            continuity=continuity,
            orientation=orientation,
            layer=layer,
            shape=shape,
            status=bar_status,
            traceability=traceability,
            calculation_readiness=readiness,
        )

        group = build_reinforcement_group(
            group_id=group_id,
            beam_id=beam_id,
            context_id=context_id,
            specification_id=specification_id,
            bars=[bar],
            group_type=reinforcement_type,
            engineering_role=role,
            status=group_status,
            traceability=traceability,
            calculation_readiness=readiness,
        )

        return bar, group

    @staticmethod
    def _resolve_role(reinforcement_type: str) -> str:
        return SPECIFICATION_TYPE_TO_ROLE.get(reinforcement_type, ROLE_UNKNOWN)

    @staticmethod
    def _resolve_position(spec: dict[str, Any], role: str) -> str:
        zone = spec.get("zone")
        level = spec.get("level")
        if zone:
            return str(zone)
        if level:
            return str(level)
        return ROLE_TO_POSITION.get(role, "UNKNOWN")

    @staticmethod
    def _resolve_continuity(spec: dict[str, Any]) -> str:
        notes = str(spec.get("notes") or "").upper()
        callout = str(spec.get("callout") or "").upper()
        if "CONT" in notes or "CONT" in callout:
            return "CONTINUOUS"
        if spec.get("specification_status") == "DEFERRED":
            return "UNKNOWN"
        return "STANDARD"

    @staticmethod
    def _resolve_bar_status(
        quantity: Optional[int],
        diameter_mm: Optional[float],
        role: str,
        steel_grade: Any,
    ) -> str:
        if (
            quantity is not None
            and quantity > 0
            and diameter_mm is not None
            and diameter_mm > 0
            and role != ROLE_UNKNOWN
            and steel_grade
        ):
            return STATUS_NORMALIZED
        if quantity is not None and diameter_mm is not None:
            return STATUS_PARTIAL
        return STATUS_INCOMPLETE

    @staticmethod
    def _build_traceability(
        spec: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "lineage": [
                "Reinforcement Calculation",
                "Engineering Calculation Context",
                "Engineering Specification",
                "Resolved Property",
                "Engineering Object",
            ],
            "specification_id": spec.get("specification_id"),
            "context_id": context.get("context_id"),
            "engineering_object_id": spec.get("engineering_object_id"),
            "reinforcement_type": spec.get("reinforcement_type"),
            "specification_status": spec.get("specification_status"),
            "callout": spec.get("callout"),
            "specification_traceability": spec.get("traceability", {}),
            "context_traceability": context.get("traceability", {}),
        }


def _parse_quantity(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
        match = re.search(r"(\d+)", stripped)
        if match:
            return int(match.group(1))
    return None


def _parse_diameter_mm(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"(\d+(?:\.\d+)?)", value)
        if match:
            return float(match.group(1))
    return None
