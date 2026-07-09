"""Validate recovery lineage from registry through production outputs."""

from __future__ import annotations

from typing import Any, Dict, List


class LineageValidator:
    """Verify end-to-end recovery lineage consistency."""

    def validate(self, snapshot: dict[str, Any], authoritative: dict[str, Any]) -> dict[str, Any]:
        chains: List[dict[str, Any]] = []
        for phase, entries, source in (
            ("J.1", snapshot.get("j1_registry_entries") or [], "QA.COVERAGE.5"),
            ("J.2", snapshot.get("j2_registry_entries") or [], "Phase J.2"),
        ):
            for entry in entries:
                chains.append(self._validate_entry(entry, snapshot, source))

        failed = [item for item in chains if item.get("status") == "FAIL"]
        return {
            "chain_count": len(chains),
            "passed": len(chains) - len(failed),
            "failed": len(failed),
            "chains": chains,
            "status": "PASS" if not failed else "FAIL",
        }

    @staticmethod
    def _validate_entry(entry: dict[str, Any], snapshot: dict[str, Any], source: str) -> dict[str, Any]:
        discovery_id = str(entry.get("discovery_id") or "")
        bar_id = str(entry.get("normalized_bar_id") or "")
        bars_by_id = {
            str(bar.get("bar_id") or ""): bar for bar in snapshot.get("bars") or [] if bar.get("bar_id")
        }
        bar = bars_by_id.get(bar_id, {})
        trace = bar.get("traceability") or {}
        steel_results = snapshot.get("steel_weight_results") or []
        steel = next((item for item in steel_results if item.get("bar_id") == bar_id), None)
        bbs_bar_ids = LineageValidator._bbs_bar_ids(snapshot.get("bbs_results") or [])

        stages = {
            "recovery_registry": bool(entry.get("recovery_id") or entry.get("expansion_id")),
            "engineering_object": bool(entry.get("recovered_object_id")),
            "normalized_bar": bool(bar_id and bar),
            "calculation": bool(bar.get("calculation_readiness") or bar.get("status")),
            "steel": bool(steel),
            "bbs": bar_id in bbs_bar_ids,
            "excel": bool(snapshot.get("excel_export_registry")),
            "traceability": trace.get("discovery_id") == discovery_id,
            "recovery_source": trace.get("recovery_source") == source,
        }
        missing = [name for name, ok in stages.items() if not ok]
        return {
            "phase": source,
            "discovery_id": discovery_id,
            "bar_id": bar_id,
            "recovery_id": entry.get("recovery_id") or entry.get("expansion_id"),
            "stages": stages,
            "missing_stages": missing,
            "status": "PASS" if not missing else "FAIL",
        }

    @staticmethod
    def _bbs_bar_ids(bbs_results: List[dict[str, Any]]) -> set[str]:
        bar_ids: set[str] = set()
        for item in bbs_results:
            bar_id = str(item.get("bar_id") or "")
            if bar_id:
                bar_ids.add(bar_id)
            for member_id in item.get("member_bar_ids") or []:
                bar_ids.add(str(member_id))
        return bar_ids
