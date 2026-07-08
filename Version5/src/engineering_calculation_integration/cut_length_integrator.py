"""Report cut length integration for recovered bars."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculation_integration.integration_helpers import (
    collect_bbs_bar_ids,
    index_calc_results,
    is_cut_length_generated,
    is_steel_generated,
)


class CutLengthIntegrator:
    """Summarize cut length production integration for recovered bars."""

    @staticmethod
    def build_report(
        snapshot: dict[str, Any],
        cut_length_results: List[dict[str, Any]],
        calc_results: List[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        by_bar = {str(item.get("bar_id") or ""): item for item in cut_length_results if item.get("bar_id")}
        cut_calc = index_calc_results(calc_results or [], "CUT_LENGTH")
        records: List[dict[str, Any]] = []
        for bar_id in snapshot.get("recovered_bar_ids") or []:
            registry_entry = snapshot.get("registry_by_bar", {}).get(bar_id, {})
            record = by_bar.get(bar_id, {})
            calc_result = cut_calc.get(bar_id, {})
            generated = is_cut_length_generated(record, calc_result)
            records.append(
                {
                    "recovery_id": registry_entry.get("recovery_id"),
                    "bar_id": bar_id,
                    "cut_length_mm": record.get("cut_length_mm") or record.get("value") or calc_result.get("result_value"),
                    "result_status": record.get("result_status") or calc_result.get("result_status"),
                    "determination_state": record.get("determination_state"),
                    "generated": generated,
                }
            )
        return {
            "recovered_count": len(records),
            "generated_count": sum(1 for item in records if item["generated"]),
            "records": records,
        }
