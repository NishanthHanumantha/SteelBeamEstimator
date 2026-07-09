"""Calculation provenance export helpers."""

from __future__ import annotations

from typing import Any, List


class CalculationProvenanceExporter:
    """Serialize calculation provenance artifacts for pipeline export."""

    @staticmethod
    def export_results(results: List[dict[str, Any]]) -> dict[str, Any]:
        provenance_records = []
        for result in results:
            provenance = result.get("calculation_provenance")
            if not provenance:
                continue
            provenance_records.append(
                {
                    "result_id": result.get("result_id"),
                    "calculation_type": result.get("calculation_type"),
                    "calculation_state": result.get("calculation_state"),
                    "calculation_provenance": provenance,
                }
            )
        return {
            "phase": "Phase I.5.A",
            "provenance_count": len(provenance_records),
            "records": provenance_records,
        }

    @staticmethod
    def export_validation(validation: dict[str, Any]) -> dict[str, Any]:
        return validation
