"""Material quantification summary — Phase I.14."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.material_quantification.material_types import (
    CREATED_PHASE,
    MaterialState,
)


class MaterialSummary:
    """Build project-level material quantification statistics."""

    @staticmethod
    def build(
        quantity_records: List[dict[str, Any]],
        material_records: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        weights = [float(item.get("total_weight_kg") or 0.0) for item in material_records]
        cut_lengths = [int(item.get("total_cut_length_mm") or 0) for item in material_records]
        bar_counts = [int(item.get("total_bar_count") or 0) for item in material_records]
        record_count = len(material_records)

        material_types = sorted({str(item.get("material_type", "")) for item in material_records if item.get("material_type")})
        steel_grades = sorted({str(item.get("steel_grade", "")) for item in material_records if item.get("steel_grade")})
        diameters = sorted({
            int(item.get("diameter_mm"))
            for item in material_records
            if item.get("diameter_mm") is not None
        })

        ready_materials = sum(
            1 for item in material_records
            if item.get("material_state") == MaterialState.READY.value
        )
        deferred_materials = sum(
            1 for item in material_records
            if item.get("material_state") == MaterialState.DEFERRED.value
        )
        blocked_materials = sum(
            1 for item in material_records
            if item.get("material_state") == MaterialState.BLOCKED.value
        )
        empty_materials = sum(
            1 for item in material_records
            if item.get("material_state") == MaterialState.EMPTY.value
        )
        unknown_materials = sum(
            1 for item in material_records
            if item.get("material_state") == MaterialState.UNKNOWN.value
        )

        return {
            "phase": "Phase I.14",
            "framework_phase": CREATED_PHASE,
            "total_quantities": len(quantity_records),
            "total_material_records": record_count,
            "material_types": material_types,
            "steel_grades": steel_grades,
            "diameters_mm": diameters,
            "ready_materials": ready_materials,
            "deferred_materials": deferred_materials,
            "blocked_materials": blocked_materials,
            "empty_materials": empty_materials,
            "unknown_materials": unknown_materials,
            "total_steel_weight_kg": round(sum(weights), 3),
            "total_cut_length_mm": sum(cut_lengths),
            "total_bars": sum(bar_counts),
            "average_weight_per_material_kg": round(sum(weights) / record_count, 3) if record_count else 0.0,
            "average_bars_per_material": round(sum(bar_counts) / record_count, 2) if record_count else 0.0,
            "registry_statistics": {
                "namespace": registry.get("namespace"),
                "determination_count": registry.get("determination_count", 0),
                "state_counts": registry.get("state_counts", {}),
            },
            "validation_summary": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
        }
