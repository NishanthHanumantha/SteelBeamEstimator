"""Derive authoritative recovery metrics from production artifacts."""

from __future__ import annotations

from typing import Any, Dict, List, Set


J1_RECOVERY_SOURCE = "QA.COVERAGE.5"
J2_RECOVERY_SOURCE = "Phase J.2"


class ProductionSnapshot:
    """Build single-source-of-truth production metrics."""

    @staticmethod
    def build(snapshot: dict[str, Any]) -> dict[str, Any]:
        bars = snapshot.get("bars") or []
        inventory = snapshot.get("inventory") or []
        j1_entries = snapshot.get("j1_registry_entries") or []
        j2_entries = snapshot.get("j2_registry_entries") or []
        objects = snapshot.get("engineering_objects") or []

        native_bars = [bar for bar in bars if not (bar.get("traceability") or {}).get("recovery_source")]
        j1_bars = [
            bar
            for bar in bars
            if str((bar.get("traceability") or {}).get("recovery_source") or "") == J1_RECOVERY_SOURCE
        ]
        j2_bars = [
            bar
            for bar in bars
            if str((bar.get("traceability") or {}).get("recovery_source") or "") == J2_RECOVERY_SOURCE
        ]
        recovered_bars = [bar for bar in bars if (bar.get("traceability") or {}).get("recovery_source")]

        j1_discovery_ids = {
            str(entry.get("discovery_id"))
            for entry in j1_entries
            if entry.get("discovery_id") and entry.get("recovery_status") == "SUCCESS"
        }
        j2_discovery_ids = {
            str(entry.get("discovery_id"))
            for entry in j2_entries
            if entry.get("discovery_id") and entry.get("recovery_status") == "SUCCESS"
        }
        bar_discovery_ids = {
            str((bar.get("traceability") or {}).get("discovery_id"))
            for bar in bars
            if (bar.get("traceability") or {}).get("discovery_id")
        }

        inventory_count = len(inventory)
        total_bars = len(bars)
        native_count = len(native_bars)
        j1_count = len(j1_bars)
        j2_count = len(j2_bars)
        j1_registry_count = len(j1_entries)
        j2_registry_count = len(j2_entries)

        pre_j1_bars = native_count
        post_j1_bars = native_count + j1_count
        post_all_recovery_bars = total_bars

        metrics = {
            "inventory_count": inventory_count,
            "total_production_bars": total_bars,
            "native_bars": native_count,
            "j1_recovered_bars": j1_count,
            "j2_recovered_bars": j2_count,
            "total_recovered_bars": len(recovered_bars),
            "j1_registry_count": j1_registry_count,
            "j2_registry_count": j2_registry_count,
            "engineering_object_count": len(objects),
            "pre_j1_bars": pre_j1_bars,
            "post_j1_bars": post_j1_bars,
            "post_all_recovery_bars": post_all_recovery_bars,
            "normalization_coverage_percent": ProductionSnapshot._coverage(total_bars, inventory_count),
            "pre_j1_coverage_percent": ProductionSnapshot._coverage(pre_j1_bars, inventory_count),
            "post_j1_coverage_percent": ProductionSnapshot._coverage(post_j1_bars, inventory_count),
            "j1_delta_bars": j1_count,
            "j2_delta_bars": j2_count,
            "j1_discovery_ids": sorted(j1_discovery_ids),
            "j2_discovery_ids": sorted(j2_discovery_ids),
            "bar_discovery_ids": sorted(bar_discovery_ids),
            "steel_weight_results_count": len(snapshot.get("steel_weight_results") or []),
            "bbs_results_count": len(snapshot.get("bbs_results") or []),
            "beam_schedule_results_count": len(snapshot.get("beam_schedule_results") or []),
        }
        metrics["authoritative_sources"] = ProductionSnapshot._source_map()
        metrics["internal_consistency"] = {
            "native_plus_j1_plus_j2_equals_total": native_count + j1_count + j2_count == total_bars,
            "j1_registry_matches_production": j1_count == j1_registry_count,
            "j2_registry_matches_production": j2_count == j2_registry_count,
            "registry_discovery_subset_of_bars": j1_discovery_ids | j2_discovery_ids <= bar_discovery_ids,
        }
        return metrics

    @staticmethod
    def _coverage(bar_count: int, inventory_count: int) -> float:
        if inventory_count <= 0:
            return 0.0
        return round((bar_count / inventory_count) * 100, 2)

    @staticmethod
    def _source_map() -> Dict[str, str]:
        return {
            "j1_recovered_count": "recovery_registry.json",
            "j2_recovered_count": "expansion_registry.json",
            "total_production_bars": "reinforcement_objects.json",
            "native_bars": "reinforcement_objects.json (no recovery_source)",
            "normalization_coverage_percent": "reinforcement_objects.json + reinforcement_inventory.json",
            "pre_j1_coverage_percent": "reinforcement_objects.json (native) + inventory",
            "post_j1_coverage_percent": "reinforcement_objects.json (native+j1) + inventory",
            "steel_weight": "steel_weight_results.json",
            "bbs_rows": "beam_schedule_results.json",
            "excel_rows": "excel_export_registry.json",
        }
