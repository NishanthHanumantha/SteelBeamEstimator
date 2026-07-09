"""Material quantification export helpers — Phase I.14."""

from __future__ import annotations

from typing import Any, List


class MaterialExporter:
    """Serialize material quantification artifacts for pipeline export."""

    @staticmethod
    def export_results(records: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase I.14",
            "determination_count": len(records),
            "results": records,
        }

    @staticmethod
    def export_registry(registry: dict[str, Any]) -> dict[str, Any]:
        return registry

    @staticmethod
    def export_statistics(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.14",
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
        }

    @staticmethod
    def export_report(reporting: dict[str, Any]) -> dict[str, Any]:
        return reporting

    @staticmethod
    def export_engineering_material_report(
        summary: dict[str, Any],
        reporting: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "phase": "Phase I.14",
            "title": "Engineering Material Quantification Report",
            "summary": summary,
            "reporting": reporting,
        }
