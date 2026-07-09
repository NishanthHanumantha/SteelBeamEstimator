"""Quantity contribution classification for recovered objects."""

from __future__ import annotations

from typing import Any, List


class ContributionAnalyzer:
    """Report steel, BBS, Excel, and QA contribution for recovered objects."""

    def analyze(
        self,
        snapshot: dict[str, Any],
        steel_validation: dict[str, Any],
        bbs_validation: dict[str, Any],
        excel_validation: dict[str, Any],
        quantity_traceability: dict[str, Any],
    ) -> dict[str, Any]:
        steel_by_bar = {item.get("bar_id"): item for item in steel_validation.get("records") or []}
        bbs_by_bar = {item.get("bar_id"): item for item in bbs_validation.get("records") or []}
        excel_by_bar = {item.get("bar_id"): item for item in excel_validation.get("records") or []}
        trace_by_bar = {item.get("bar_id"): item for item in quantity_traceability.get("traces") or []}

        records: List[dict[str, Any]] = []
        for bar_id in snapshot.get("recovery_index", {}).get("recovered_bar_ids") or []:
            steel = steel_by_bar.get(bar_id, {})
            bbs = bbs_by_bar.get(bar_id, {})
            excel = excel_by_bar.get(bar_id, {})
            trace = trace_by_bar.get(bar_id, {})

            contributions = {
                "steel": "YES" if steel.get("contributes_steel") else "NO",
                "bbs": "YES" if bbs.get("contributes_bbs") else "NO",
                "excel": "YES" if excel.get("contributes_excel") else "NO",
                "qa": "YES" if trace.get("current_quantity_state") == "QA_VISIBLE" else "NO",
            }
            yes_count = sum(1 for value in contributions.values() if value == "YES")
            if yes_count == 0:
                classification = "NONE"
            elif yes_count == 4:
                classification = "FULL"
            else:
                classification = "PARTIAL"

            records.append(
                {
                    "recovery_id": trace.get("recovery_id"),
                    "discovery_id": trace.get("discovery_id"),
                    "bar_id": bar_id,
                    "beam_id": trace.get("beam_id"),
                    "contribution": contributions,
                    "contribution_classification": classification,
                    "reason": trace.get("primary_blocking_reason"),
                    "current_quantity_state": trace.get("current_quantity_state"),
                    "first_failure_stage": trace.get("first_failure_stage"),
                }
            )

        return {
            "recovered_count": len(records),
            "records": records,
            "summary": {
                "steel_contributors": sum(1 for item in records if item["contribution"]["steel"] == "YES"),
                "bbs_contributors": sum(1 for item in records if item["contribution"]["bbs"] == "YES"),
                "excel_contributors": sum(1 for item in records if item["contribution"]["excel"] == "YES"),
                "qa_contributors": sum(1 for item in records if item["contribution"]["qa"] == "YES"),
                "none_classification": sum(1 for item in records if item["contribution_classification"] == "NONE"),
                "partial_classification": sum(1 for item in records if item["contribution_classification"] == "PARTIAL"),
                "full_classification": sum(1 for item in records if item["contribution_classification"] == "FULL"),
            },
        }
