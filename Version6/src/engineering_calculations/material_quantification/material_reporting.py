"""Material quantification reporting — Phase I.14."""

from __future__ import annotations

from typing import Any

from src.engineering_calculations.material_quantification.material_summary import MaterialSummary


class MaterialReporting:
    """Single source of truth for material validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        quantity_records = model.get("quantity_results", [])
        material_records = model.get("material_results", [])
        registry = model.get("material_registry", {})
        model["material_validation"] = validation
        model["material_summary"] = MaterialSummary.build(
            quantity_records,
            material_records,
            registry,
            validation,
        )
        model["material_reporting"] = MaterialReporting.build(
            model["material_summary"],
            validation,
        )

    @staticmethod
    def build(summary: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.14",
            "status": validation.get("status", "SKIP"),
            "total_quantities": summary.get("total_quantities", 0),
            "total_material_records": summary.get("total_material_records", 0),
            "material_types": summary.get("material_types", []),
            "steel_grades": summary.get("steel_grades", []),
            "diameters_mm": summary.get("diameters_mm", []),
            "ready_materials": summary.get("ready_materials", 0),
            "deferred_materials": summary.get("deferred_materials", 0),
            "blocked_materials": summary.get("blocked_materials", 0),
            "empty_materials": summary.get("empty_materials", 0),
            "unknown_materials": summary.get("unknown_materials", 0),
            "total_steel_weight_kg": summary.get("total_steel_weight_kg", 0.0),
            "total_cut_length_mm": summary.get("total_cut_length_mm", 0),
            "total_bars": summary.get("total_bars", 0),
            "average_weight_per_material_kg": summary.get("average_weight_per_material_kg", 0.0),
            "average_bars_per_material": summary.get("average_bars_per_material", 0.0),
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
            "checks_passed": validation.get("summary", {}).get("passed", 0),
            "checks_failed": validation.get("summary", {}).get("failed", 0),
            "checks_total": validation.get("summary", {}).get("total_checks", 0),
        }
