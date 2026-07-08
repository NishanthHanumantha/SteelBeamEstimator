"""Excel export integration validation for recovered bars."""

from __future__ import annotations

from typing import Any, List


class ExcelValidator:
    """Determine Excel eligibility, visibility, and aggregation for recovered bars."""

    def validate(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        recovery_index = snapshot.get("recovery_index") or {}
        recovered_bar_ids = recovery_index.get("recovered_bar_ids") or []
        excel_stats = snapshot.get("excel_statistics") or {}
        registries = snapshot.get("registries") or {}
        records: List[dict[str, Any]] = []

        for bar_id in recovered_bar_ids:
            bar = snapshot.get("bar_by_id", {}).get(bar_id, {})
            registry_entry = (recovery_index.get("registry_by_bar") or {}).get(bar_id, {})
            steel = snapshot.get("steel_weight_by_bar", {}).get(bar_id, {})
            bbs = snapshot.get("bbs_by_bar", {}).get(bar_id)

            eligible = bar.get("status") == "NORMALIZED"
            written = bar_id in str(registries.get("excel_export") or {}) or bar_id in str(registries.get("steel_weight") or {})
            visible = steel.get("weight_kg") is not None or bbs is not None
            aggregated = int(excel_stats.get("rows_written") or 0) > 0

            failure_reasons = []
            if not eligible:
                failure_reasons.append("Bar not export eligible")
            if steel.get("status") == "DEFERRED":
                failure_reasons.append("Deferred steel weight prevents Excel quantity row")
            if not visible:
                failure_reasons.append("Recovered bar not visible in export source registries")
            if not written:
                failure_reasons.append("Recovered bar not written to Excel export registry")
            if not aggregated:
                failure_reasons.append("Excel summary not updated with recovered quantities")

            records.append(
                {
                    "recovery_id": registry_entry.get("recovery_id"),
                    "bar_id": bar_id,
                    "beam_id": bar.get("beam_id") or registry_entry.get("beam_id"),
                    "eligible": eligible,
                    "written": written,
                    "visible": visible,
                    "aggregated": aggregated,
                    "contributes_excel": visible and written and aggregated,
                    "excel_rows_written": excel_stats.get("rows_written"),
                    "failure_reasons": failure_reasons,
                    "first_failure": failure_reasons[0] if failure_reasons else None,
                }
            )

        return {
            "recovered_count": len(records),
            "excel_contributors": sum(1 for item in records if item["contributes_excel"]),
            "records": records,
            "workbook_rows_written": excel_stats.get("rows_written"),
        }
