"""Verify recovered calculation contexts use existing production builder outputs."""

from __future__ import annotations

from typing import Any, List


class CalculationContextIntegrator:
    """Report calculation context integration for recovered bars."""

    @staticmethod
    def build_report(snapshot: dict[str, Any], contexts: List[dict[str, Any]]) -> dict[str, Any]:
        context_by_id = {str(item.get("context_id") or ""): item for item in contexts}
        records: List[dict[str, Any]] = []
        for bar_id in snapshot.get("recovered_bar_ids") or []:
            bar = next((item for item in snapshot.get("bars") or [] if item.get("bar_id") == bar_id), {})
            registry_entry = snapshot.get("registry_by_bar", {}).get(bar_id, {})
            context = context_by_id.get(str(bar.get("context_id") or ""), {})
            records.append(
                {
                    "recovery_id": registry_entry.get("recovery_id"),
                    "bar_id": bar_id,
                    "context_id": context.get("context_id") or bar.get("context_id"),
                    "engineering_length_mm": context.get("effective_span_mm") or context.get("clear_span_mm"),
                    "calculation_state": context.get("calculation_status"),
                    "dependency_set_complete": context.get("calculation_status") == "COMPLETE",
                    "availability_state": context.get("availability") or context.get("availability_state"),
                    "lifecycle_state": context.get("lifecycle_state") or context.get("engineering_state"),
                }
            )
        return {
            "recovered_count": len(records),
            "records": records,
            "context_count": len(contexts),
        }
