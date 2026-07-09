"""Engineering traceability matrix for reinforcement annotations."""

from __future__ import annotations

from typing import Any, Dict, List


class TraceabilityReportBuilder:
    """Generate trace records for every reinforcement annotation."""

    COLUMNS = (
        "discovery_id",
        "original_text",
        "coordinates",
        "beam",
        "category",
        "normalized_bar_id",
        "calculation_state",
        "bbs_row_id",
        "excel_row_number",
        "failure_stage",
        "failure_reason",
        "current_status",
    )

    def build(self, inventory: List[dict[str, Any]]) -> dict[str, Any]:
        records: List[dict[str, Any]] = []
        for item in inventory:
            records.append(
                {
                    "discovery_id": item.get("discovery_id"),
                    "original_text": item.get("original_text"),
                    "coordinates": item.get("coordinates"),
                    "beam": item.get("beam_association"),
                    "category": item.get("category"),
                    "normalized_bar_id": item.get("normalized_bar_id"),
                    "calculation_state": item.get("calculation_state"),
                    "bbs_row_id": item.get("bbs_row_id"),
                    "excel_row_number": item.get("excel_row_number"),
                    "failure_stage": item.get("failure_stage"),
                    "failure_reason": item.get("failure_reason"),
                    "current_status": item.get("current_status"),
                    "geometry_id": item.get("geometry_id"),
                    "pipeline_trace": item.get("pipeline_trace"),
                }
            )
        success = sum(1 for item in records if item.get("current_status") == "WRITTEN_TO_EXCEL")
        lost = sum(
            1
            for item in records
            if str(item.get("current_status", "")).endswith("FAILED")
            or item.get("current_status") in {"DISCOVERY_FAILED", "ASSOCIATION_FAILED", "NORMALIZATION_FAILED"}
        )
        return {
            "columns": list(self.COLUMNS),
            "record_count": len(records),
            "success_count": success,
            "lost_count": lost,
            "records": records,
        }

    def build_callout_traces(self, inventory: List[dict[str, Any]]) -> List[dict[str, Any]]:
        traces: List[dict[str, Any]] = []
        for item in inventory:
            traces.append(
                {
                    "discovery_id": item.get("discovery_id"),
                    "original_text": item.get("original_text"),
                    "location": item.get("coordinates"),
                    "beam": item.get("beam_association") or "UNKNOWN",
                    "classification": item.get("classification"),
                    "normalized": "YES" if item.get("normalized_bar_id") else "NO",
                    "calculated": "YES"
                    if item.get("pipeline_trace", {}).get("calculated")
                    else "NO",
                    "excel": "YES"
                    if item.get("pipeline_trace", {}).get("written_to_excel")
                    else "NO",
                    "status": "SUCCESS"
                    if item.get("current_status") == "WRITTEN_TO_EXCEL"
                    else item.get("current_status"),
                }
            )
        return traces
