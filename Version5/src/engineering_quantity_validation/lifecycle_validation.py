"""Lifecycle and availability validation for recovered objects."""

from __future__ import annotations

from typing import Any, List


class LifecycleValidator:
    """Inspect lifecycle transitions and export blockers for recovered bars."""

    def validate(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        recovery_index = snapshot.get("recovery_index") or {}
        recovered_bar_ids = recovery_index.get("recovered_bar_ids") or []
        records: List[dict[str, Any]] = []

        for bar_id in recovered_bar_ids:
            bar = snapshot.get("bar_by_id", {}).get(bar_id, {})
            registry_entry = (recovery_index.get("registry_by_bar") or {}).get(bar_id, {})
            context = snapshot.get("context_by_id", {}).get(str(bar.get("context_id") or ""), {})
            readiness = snapshot.get("readiness_by_bar", {}).get(bar_id)
            steel = snapshot.get("steel_weight_by_bar", {}).get(bar_id, {})
            identity = snapshot.get("bar_identity_by_bar", {}).get(bar_id, {})

            lifecycle_state = (
                context.get("lifecycle_state")
                or context.get("engineering_state")
                or (context.get("lifecycle") or {}).get("current_state")
            )
            availability = context.get("availability") or context.get("availability_state")
            export_state = steel.get("fabrication_state") or identity.get("fabrication_state")

            blockers: List[str] = []
            if readiness is None:
                blockers.append("Recovered bar missing from calculation readiness registry")
            if str(steel.get("status") or "").upper() == "DEFERRED":
                blockers.append("Deferred steel weight lifecycle")
            if str(identity.get("determination_state") or "").upper() == "DEFERRED":
                blockers.append("Bar identity determination deferred")
            if str(identity.get("result_status") or "") == "PRESERVED_DEFERRED":
                blockers.append("Bar identity preserved deferred")
            if export_state and "DEFERRED" in str(export_state).upper():
                blockers.append("Export-disabled fabrication state")

            records.append(
                {
                    "recovery_id": registry_entry.get("recovery_id"),
                    "bar_id": bar_id,
                    "beam_id": bar.get("beam_id") or registry_entry.get("beam_id"),
                    "lifecycle_transitions": {
                        "engineering_object": "OBJECT_CREATED",
                        "normalization": bar.get("status"),
                        "calculation_readiness": (readiness or {}).get("calculation_readiness"),
                        "steel_weight": steel.get("status") or steel.get("result_status"),
                        "export": export_state,
                        "qa": "NOT_VISIBLE",
                    },
                    "lifecycle_state": lifecycle_state,
                    "availability_state": availability,
                    "hidden_blockers": blockers,
                    "primary_lifecycle_blocker": blockers[0] if blockers else None,
                }
            )

        return {
            "recovered_count": len(records),
            "records": records,
            "summary": {
                "missing_readiness": sum(1 for item in records if "readiness registry" in str(item.get("hidden_blockers"))),
                "deferred_identity": sum(
                    1 for item in records if any("identity" in blocker.lower() for blocker in item.get("hidden_blockers") or [])
                ),
                "deferred_steel": sum(
                    1 for item in records if any("steel weight" in blocker.lower() for blocker in item.get("hidden_blockers") or [])
                ),
            },
        }
