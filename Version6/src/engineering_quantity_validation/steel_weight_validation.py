"""Steel weight integration validation for recovered bars."""

from __future__ import annotations

from typing import Any, Dict, List


class SteelWeightValidator:
    """Determine why recovered bars do or do not contribute steel weight."""

    BLOCKER_CATALOG = (
        "Missing cut length",
        "Missing engineering length",
        "Calculation deferred",
        "Weight engine deferred",
        "Aggregation skipped",
        "Registry missing",
        "Serialization missing",
        "Unknown dependency",
    )

    def validate(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        recovery_index = snapshot.get("recovery_index") or {}
        recovered_bar_ids = recovery_index.get("recovered_bar_ids") or []
        records: List[dict[str, Any]] = []

        for bar_id in recovered_bar_ids:
            bar = snapshot.get("bar_by_id", {}).get(bar_id, {})
            steel = snapshot.get("steel_weight_by_bar", {}).get(bar_id, {})
            calc_results = snapshot.get("calc_by_bar", {}).get(bar_id, [])
            cut_length = snapshot.get("cut_length_by_bar", {}).get(bar_id)
            registry_entry = (recovery_index.get("registry_by_bar") or {}).get(bar_id, {})
            registries = snapshot.get("registries") or {}

            blockers = self._identify_blockers(bar, steel, calc_results, cut_length, registries, bar_id)
            records.append(
                {
                    "recovery_id": registry_entry.get("recovery_id"),
                    "bar_id": bar_id,
                    "beam_id": bar.get("beam_id") or registry_entry.get("beam_id"),
                    "contributes_steel": steel.get("weight_kg") is not None and float(steel.get("weight_kg") or 0) > 0,
                    "steel_status": steel.get("status") or steel.get("result_status"),
                    "weight_kg": steel.get("weight_kg"),
                    "cut_length_mm": steel.get("cut_length_mm") or steel.get("cut_length"),
                    "blockers": blockers,
                    "primary_blocker": blockers[0] if blockers else None,
                    "in_steel_registry": bar_id in str(registries.get("steel_weight") or {}),
                    "trace": steel.get("trace") or [],
                }
            )

        contributors = [item for item in records if item["contributes_steel"]]
        return {
            "recovered_count": len(records),
            "steel_contributors": len(contributors),
            "records": records,
            "summary": {
                "all_deferred": all(item.get("steel_status") == "DEFERRED" for item in records),
                "missing_cut_length": sum(1 for item in records if "Missing cut length" in item.get("blockers", [])),
                "registry_present": sum(1 for item in records if item.get("in_steel_registry")),
            },
        }

    def _identify_blockers(
        self,
        bar: dict[str, Any],
        steel: dict[str, Any],
        calc_results: List[dict[str, Any]],
        cut_length: dict[str, Any] | None,
        registries: dict[str, Any],
        bar_id: str,
    ) -> List[str]:
        blockers: List[str] = []
        calc_by_type = {
            str(item.get("calculation_type") or ""): item for item in calc_results if item.get("calculation_type")
        }

        if cut_length is None and steel.get("cut_length_mm") is None and steel.get("cut_length") is None:
            blockers.append("Missing cut length")
        if steel.get("engineering_length") is None and bar.get("length") is None:
            blockers.append("Missing engineering length")

        for calc_type in ("BAR_IDENTITY", "SHAPE_CODE", "CUT_LENGTH"):
            result = calc_by_type.get(calc_type, {})
            status = str(result.get("result_status") or "").upper()
            if status in {"DEPENDENCY_BLOCKED", "FAILED", "BLOCKED"}:
                blockers.append(f"{calc_type} {status}")

        steel_calc = calc_by_type.get("STEEL_WEIGHT", {})
        if str(steel_calc.get("calculation_state") or "").upper() == "DEFERRED":
            blockers.append("Calculation deferred")
        if str(steel.get("status") or "").upper() == "DEFERRED":
            blockers.append("Weight engine deferred")
        if steel.get("weight_kg") is None:
            blockers.append("Aggregation skipped")
        if bar_id not in str(registries.get("steel_weight") or {}):
            blockers.append("Registry missing")
        if not steel:
            blockers.append("Serialization missing")
        if not blockers:
            blockers.append("Unknown dependency")
        return blockers
