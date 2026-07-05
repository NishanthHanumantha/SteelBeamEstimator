"""Engineering quantity builder — Phase I.13."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_calculations.quantity.quantity_types import (
    DETERMINATION_METHOD,
    CREATED_PHASE,
    QuantityState,
)
from src.engineering_calculations.material_quantification.material_types import (
    DEFAULT_STEEL_GRADE,
    MATERIAL_TYPE_REINFORCEMENT_STEEL,
)


class QuantityBuilder:
    """Aggregate beam summary outputs into deterministic quantity records."""

    @staticmethod
    def build(summary: dict[str, Any]) -> dict[str, Any]:
        completion = dict(summary.get("completion") or {})
        quality = dict(summary.get("quality") or {})
        provenance = dict(summary.get("calculation_provenance") or summary.get("provenance") or {})
        engineering_ready = bool(completion.get("engineering_ready"))
        quality_ready = bool(quality.get("quality_ready"))
        quantity_state = QuantityBuilder._resolve_quantity_state(
            summary,
            completion,
            quality,
        )
        diameters = list(summary.get("diameters") or [])
        diameter_mm = int(diameters[0]) if len(diameters) == 1 else None

        return {
            "quantity_id": None,
            "beam_summary_id": summary.get("beam_summary_id"),
            "beam_id": summary.get("beam_id"),
            "beam_mark": summary.get("beam_mark"),
            "engineering_ready": engineering_ready,
            "quality_ready": quality_ready,
            "quantity_state": quantity_state,
            "steel_weight_kg": summary.get("total_steel_weight_kg", 0.0),
            "cut_length_mm": summary.get("total_cut_length_mm", 0),
            "bar_count": summary.get("bar_count", 0),
            "fabrication_marks": list(summary.get("fabrication_marks") or []),
            "material_type": MATERIAL_TYPE_REINFORCEMENT_STEEL,
            "steel_grade": DEFAULT_STEEL_GRADE,
            "diameter_mm": diameter_mm,
            "engineering_state": summary.get("engineering_state"),
            "completion": completion,
            "quality": quality,
            "calculation_provenance": provenance,
            "provenance": provenance,
            "trace": list(summary.get("trace") or []),
            "traceability": dict(summary.get("traceability") or {}),
            "quantity_metadata": {
                "determination_method": DETERMINATION_METHOD,
                "source_phase": CREATED_PHASE,
                "dependency_graph_consulted": True,
            },
            "status": quantity_state,
        }

    @staticmethod
    def _resolve_quantity_state(
        summary: dict[str, Any],
        completion: dict[str, Any],
        quality: dict[str, Any],
    ) -> str:
        if not completion and not quality and int(summary.get("bar_count") or 0) == 0:
            return QuantityState.UNKNOWN.value

        bars_total = int(
            completion.get("bars_total")
            if completion.get("bars_total") is not None
            else summary.get("bar_count")
            or 0
        )
        if bars_total == 0:
            return QuantityState.EMPTY.value
        if not completion:
            return QuantityState.UNKNOWN.value
        if not bool(completion.get("engineering_ready")):
            return QuantityState.DEFERRED.value
        if not quality:
            return QuantityState.UNKNOWN.value
        if not bool(quality.get("quality_ready")):
            return QuantityState.BLOCKED.value
        return QuantityState.READY.value
