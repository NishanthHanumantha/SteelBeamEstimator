"""Recovery traceability lineage."""

from __future__ import annotations

from typing import Any, Dict, List


class RecoveryTraceabilityBuilder:
    """Build full recovery lineage chains."""

    def build_all(
        self,
        recovered_objects: List[dict[str, Any]],
        registry_entries: List[dict[str, Any]],
        normalized_bars: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        registry_by_discovery = {
            str(item.get("discovery_id")): item for item in registry_entries
        }
        bars_by_discovery = {
            str((bar.get("traceability") or {}).get("discovery_id")): bar
            for bar in normalized_bars
            if (bar.get("traceability") or {}).get("discovery_id")
        }
        chains: List[dict[str, Any]] = []
        for recovered in recovered_objects:
            discovery_id = str(recovered.get("source_discovery_id"))
            registry = registry_by_discovery.get(discovery_id, {})
            bar = bars_by_discovery.get(discovery_id, {})
            readiness = bar.get("calculation_readiness") or {}
            chains.append(
                {
                    "discovery_id": discovery_id,
                    "lineage": [
                        discovery_id,
                        "QA.COVERAGE.4",
                        recovered.get("original_suppression_reason"),
                        "QA.COVERAGE.5",
                        recovered.get("legitimacy_class"),
                        "Recovered",
                        recovered.get("recovered_object_id"),
                        "Engineering Object",
                        "Normalized",
                        bar.get("bar_id"),
                        "Calculated",
                        readiness.get("calculation_state"),
                        "BBS",
                        registry.get("bbs_row_id"),
                        "Excel",
                        registry.get("excel_row_number"),
                    ],
                    "recovery_id": recovered.get("recovery_id"),
                    "recovered_object_id": recovered.get("recovered_object_id"),
                    "normalized_bar_id": bar.get("bar_id"),
                    "specification_id": recovered.get("specification_id"),
                    "context_id": recovered.get("context_id"),
                    "recovery_confidence": recovered.get("recovery_confidence"),
                    "recovery_justification": recovered.get("recovery_justification"),
                    "evidence": {
                        "legitimacy_class": recovered.get("legitimacy_class"),
                        "coordinates": recovered.get("coordinates"),
                        "engineering_region": recovered.get("engineering_region"),
                        "support": recovered.get("support"),
                        "station": recovered.get("station"),
                    },
                }
            )
        return chains
