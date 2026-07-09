"""Register recovered bars in the production bar identity registry."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_calculation_integration.integration_helpers import (
    index_calc_results,
    is_identity_generated,
)


class BarIdentityRegistryIntegrator:
    """Summarize bar identity integration outcomes for recovered bars."""

    @staticmethod
    def build_registry_report(
        snapshot: dict[str, Any],
        identity_results: List[dict[str, Any]],
        identity_registry: dict[str, Any],
        calc_results: List[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        recovered_bar_ids = set(snapshot.get("recovered_bar_ids") or [])
        identity_calc = index_calc_results(calc_results or [], "BAR_IDENTITY")
        records: List[dict[str, Any]] = []
        for bar_id in sorted(recovered_bar_ids):
            registry_entry = snapshot.get("registry_by_bar", {}).get(bar_id, {})
            bar = next((item for item in snapshot.get("bars") or [] if item.get("bar_id") == bar_id), {})
            identity = next((item for item in identity_results if item.get("bar_id") == bar_id), {})
            calc_result = identity_calc.get(bar_id, {})
            registered = is_identity_generated(identity, calc_result)
            records.append(
                {
                    "recovery_id": registry_entry.get("recovery_id"),
                    "discovery_id": registry_entry.get("discovery_id"),
                    "bar_id": bar_id,
                    "beam_id": bar.get("beam_id") or registry_entry.get("beam_id"),
                    "engineering_object_id": registry_entry.get("recovered_object_id"),
                    "bar_identity_id": identity.get("bar_identity_id"),
                    "engineering_bar_id": identity.get("engineering_bar_id") or calc_result.get("result_value"),
                    "engineering_bar_mark": identity.get("engineering_bar_mark") or calc_result.get("result_value"),
                    "result_status": identity.get("result_status") or calc_result.get("result_status"),
                    "determination_state": identity.get("determination_state"),
                    "calculation_identity": identity.get("engineering_bar_id") or calc_result.get("result_value"),
                    "registry_index": identity.get("bar_identity_id"),
                    "lifecycle_id": bar.get("context_id"),
                    "calculation_key": (bar.get("calculation_index") or {}).get("index_id"),
                    "dependency_key": ((bar.get("calculation_index") or {}).get("references") or {}).get("BAR_IDENTITY"),
                    "registered": registered,
                }
            )
        return {
            "recovered_count": len(records),
            "registered_identities": sum(1 for item in records if item["registered"]),
            "records": records,
            "registry": identity_registry,
        }
