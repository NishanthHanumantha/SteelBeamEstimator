"""Engineering calculation result models — Phase I.2.2."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.engineering_calculations.calculation_result_types import (
    CREATED_PHASE,
    SOURCE_ENGINE_VERSION,
)


def calculation_results_applied(model: dict[str, Any]) -> bool:
    registry = model.get("calculation_result_registry", {})
    if registry.get("phase") == "Phase I.2.2" and registry.get("result_count", 0) >= 0:
        return True
    if model.get("engineering_calculation_results") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("calculation_result_framework_complete"))


def build_engineering_calculation_result(
    result_id: str,
    engine_name: str,
    calculation_type: str,
    calculation_state: str,
    input_context_id: str,
    input_bar_id: str,
    input_group_id: str,
    input_specification_id: str,
    input_association_id: str,
    input_beam_id: str,
    result_status: str,
    result_value: Any,
    result_unit: str,
    result_metadata: dict[str, Any],
    calculation_notes: str,
    calculation_trace: dict[str, Any],
    traceability: dict[str, Any],
    calculation_inputs: dict[str, Any] | None = None,
    source_engine_version: str = SOURCE_ENGINE_VERSION,
    created_timestamp: Optional[str] = None,
) -> dict[str, Any]:
    """Build an immutable engineering calculation result record."""
    return {
        "result_id": result_id,
        "engine_name": engine_name,
        "calculation_type": calculation_type,
        "calculation_state": calculation_state,
        "input_context_id": input_context_id,
        "input_bar_id": input_bar_id,
        "input_group_id": input_group_id,
        "input_specification_id": input_specification_id,
        "input_association_id": input_association_id,
        "input_beam_id": input_beam_id,
        "result_status": result_status,
        "result_value": result_value,
        "result_unit": result_unit,
        "calculation_inputs": dict(calculation_inputs or {}),
        "result_metadata": dict(result_metadata),
        "calculation_notes": calculation_notes,
        "calculation_trace": dict(calculation_trace),
        "source_engine_version": source_engine_version,
        "created_timestamp": created_timestamp
        or datetime.now(timezone.utc).isoformat(),
        "traceability": dict(traceability),
        "metadata": {
            "created_phase": CREATED_PHASE,
        },
    }
