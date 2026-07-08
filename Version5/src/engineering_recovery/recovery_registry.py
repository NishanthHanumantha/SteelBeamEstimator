"""Recovery registry management."""

from __future__ import annotations

from typing import Any, Dict, List


class RecoveryRegistry:
    """Maintain deterministic recovery registry entries."""

    def build_entries(
        self,
        recovered_objects: List[dict[str, Any]],
        decisions: List[dict[str, Any]],
        normalized_bars: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        bars_by_discovery = {}
        for bar in normalized_bars:
            discovery_id = str((bar.get("traceability") or {}).get("discovery_id") or "")
            if discovery_id:
                bars_by_discovery[discovery_id] = bar

        entries: List[dict[str, Any]] = []
        for recovered in recovered_objects:
            discovery_id = str(recovered.get("source_discovery_id"))
            bar = bars_by_discovery.get(discovery_id, {})
            entries.append(
                {
                    "recovery_id": recovered.get("recovery_id"),
                    "discovery_id": discovery_id,
                    "recovered_object_id": recovered.get("recovered_object_id"),
                    "normalized_bar_id": bar.get("bar_id"),
                    "specification_id": recovered.get("specification_id"),
                    "context_id": recovered.get("context_id"),
                    "beam_id": recovered.get("beam"),
                    "reason": recovered.get("recovery_justification"),
                    "confidence": recovered.get("recovery_confidence"),
                    "legitimacy_class": recovered.get("legitimacy_class"),
                    "recovery_status": "SUCCESS" if bar.get("bar_id") else "NORMALIZATION_PENDING",
                    "original_suppression_reason": recovered.get("original_suppression_reason"),
                }
            )
        return entries

    @staticmethod
    def build_registry_payload(entries: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "registry_count": len(entries),
            "entries": entries,
        }
