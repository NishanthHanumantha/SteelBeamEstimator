"""Report lifecycle integration for recovered bars."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculation_integration.integration_helpers import (
    collect_bbs_bar_ids,
    index_calc_results,
    is_steel_generated,
)


class LifecycleIntegrator:
    """Summarize lifecycle progression for recovered bars after integration."""

    @staticmethod
    def build_report(
        snapshot: dict[str, Any],
        steel_results: List[dict[str, Any]],
        bbs_results: List[dict[str, Any]],
        calc_results: List[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        steel_by_bar = {str(item.get("bar_id") or ""): item for item in steel_results if item.get("bar_id")}
        steel_calc = index_calc_results(calc_results or [], "STEEL_WEIGHT")
        bbs_bar_ids = collect_bbs_bar_ids(bbs_results)
        records: List[dict[str, Any]] = []
        for bar_id in snapshot.get("recovered_bar_ids") or []:
            registry_entry = snapshot.get("registry_by_bar", {}).get(bar_id, {})
            bar = next((item for item in snapshot.get("bars") or [] if item.get("bar_id") == bar_id), {})
            steel = steel_by_bar.get(bar_id, {})
            generated = is_steel_generated(steel, steel_calc.get(bar_id))
            in_bbs = bar_id in bbs_bar_ids
            records.append(
                {
                    "recovery_id": registry_entry.get("recovery_id"),
                    "bar_id": bar_id,
                    "lifecycle_transitions": {
                        "engineering_object": "OBJECT_CREATED",
                        "calculation_ready": (bar.get("calculation_readiness") or {}).get("calculation_state"),
                        "calculated": bar.get("status"),
                        "steel_generated": "YES" if generated else "NO",
                        "bbs_generated": "YES" if in_bbs else "NO",
                        "excel_generated": "PENDING_EXPORT",
                        "qa_visible": "PENDING_QA",
                    },
                    "steel_status": steel.get("status") or steel.get("result_status") or steel_calc.get(bar_id, {}).get("result_status"),
                    "bbs_status": "GROUPED" if in_bbs else None,
                }
            )
        return {
            "recovered_count": len(records),
            "records": records,
        }
