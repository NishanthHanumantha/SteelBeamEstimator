"""Build expansion candidates, decisions, and trace records."""

from __future__ import annotations

from typing import Any, Dict, List


class ExpansionBuilder:
    """Create expansion artifacts without production writes."""

    def build_candidates(
        self,
        gaps: dict[str, Any],
        classifications: Dict[str, str],
        similarities: Dict[str, dict[str, Any]],
        eligibility_results: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        pool = gaps.get("candidate_pool") or []
        eligibility_by_id = {str(item.get("discovery_id")): item for item in eligibility_results}
        candidates: List[dict[str, Any]] = []
        for index, gap in enumerate(pool, start=1):
            discovery_id = str(gap.get("discovery_id") or "")
            inventory = gap.get("inventory") or {}
            eligibility = eligibility_by_id.get(discovery_id, {})
            similarity = similarities.get(discovery_id, {})
            candidates.append(
                {
                    "candidate_id": f"EXPANSION_CANDIDATE::{index:06d}",
                    "discovery_id": discovery_id,
                    "source_object": inventory.get("geometry_id"),
                    "beam_id": inventory.get("beam_association") or gap.get("beam_id"),
                    "engineering_object_id": inventory.get("engineering_object_id"),
                    "reason": gap.get("primary_rejection_code"),
                    "similarity_score": similarity.get("similarity_score"),
                    "expansion_class": classifications.get(discovery_id),
                    "eligibility": eligibility.get("eligibility"),
                    "decision": eligibility.get("decision"),
                    "confidence": similarity.get("similarity_score"),
                    "trace": {
                        "discovery_id": discovery_id,
                        "primary_rejection_code": gap.get("primary_rejection_code"),
                        "expansion_class": classifications.get(discovery_id),
                        "similarity_components": similarity.get("components") or {},
                        "approval_reasons": eligibility.get("approval_reasons") or [],
                        "blocking_reasons": eligibility.get("blocking_reasons") or [],
                    },
                }
            )
        return candidates

    def build_decisions(self, eligibility_results: List[dict[str, Any]]) -> List[dict[str, Any]]:
        decisions: List[dict[str, Any]] = []
        for item in eligibility_results:
            decisions.append(
                {
                    "discovery_id": item.get("discovery_id"),
                    "decision": item.get("decision"),
                    "recover": item.get("recover"),
                    "expansion_class": item.get("expansion_class"),
                    "eligibility": item.get("eligibility"),
                    "similarity_score": item.get("similarity_score"),
                    "approval_reasons": item.get("approval_reasons") or [],
                    "blocking_reasons": item.get("blocking_reasons") or [],
                    "recovery_reason": item.get("recovery_reason"),
                    "beam_id": item.get("beam_id"),
                    "primary_rejection_code": item.get("primary_rejection_code"),
                }
            )
        return decisions

    def build_traceability(
        self,
        candidates: List[dict[str, Any]],
        registry_entries: List[dict[str, Any]],
        recovered_objects: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        registry_by_discovery = {
            str(entry.get("discovery_id")): entry for entry in registry_entries if entry.get("discovery_id")
        }
        recovered_by_discovery = {
            str(item.get("source_discovery_id")): item for item in recovered_objects if item.get("source_discovery_id")
        }
        candidate_by_id = {str(item.get("discovery_id")): item for item in candidates}
        chains: List[dict[str, Any]] = []
        for entry in registry_entries:
            discovery_id = str(entry.get("discovery_id") or "")
            if not discovery_id:
                continue
            candidate = candidate_by_id.get(discovery_id, {})
            recovered = recovered_by_discovery.get(discovery_id, {})
            chains.append(
                {
                    "discovery_id": discovery_id,
                    "candidate_id": candidate.get("candidate_id"),
                    "expansion_id": entry.get("expansion_id"),
                    "recovery_id": entry.get("recovery_id"),
                    "recovered_object_id": recovered.get("recovered_object_id") or entry.get("recovered_object_id"),
                    "normalized_bar_id": entry.get("normalized_bar_id"),
                    "similarity_score": entry.get("similarity_score") or candidate.get("similarity_score"),
                    "expansion_class": entry.get("expansion_class") or candidate.get("expansion_class"),
                    "primary_rejection_code": candidate.get("reason") or entry.get("original_rejection_reason"),
                    "lineage": [
                        "Discovery",
                        "Expansion Candidate",
                        "Expansion Decision",
                        "Recovered Object",
                        "Normalized Bar",
                        "Production Pipeline",
                    ],
                }
            )
        return chains

    def build_registry_entries(
        self,
        recovered_objects: List[dict[str, Any]],
        approved: List[dict[str, Any]],
        normalized_bars: List[dict[str, Any]],
        id_counters: dict[str, int],
    ) -> tuple[List[dict[str, Any]], dict[str, int]]:
        counters = dict(id_counters)
        bars_by_discovery = {
            str((bar.get("traceability") or {}).get("discovery_id")): bar
            for bar in normalized_bars
            if (bar.get("traceability") or {}).get("discovery_id")
        }
        approved_by_id = {str(item.get("discovery_id")): item for item in approved}
        entries: List[dict[str, Any]] = []
        for recovered in recovered_objects:
            discovery_id = str(recovered.get("source_discovery_id") or "")
            approved_item = approved_by_id.get(discovery_id, {})
            bar = bars_by_discovery.get(discovery_id, {})
            counters["expansion"] = counters.get("expansion", 0) + 1
            entries.append(
                {
                    "expansion_id": f"EXPANSION::{counters['expansion']:06d}",
                    "recovery_id": recovered.get("recovery_id"),
                    "discovery_id": discovery_id,
                    "recovered_object_id": recovered.get("recovered_object_id"),
                    "normalized_bar_id": bar.get("bar_id"),
                    "specification_id": recovered.get("specification_id"),
                    "context_id": recovered.get("context_id"),
                    "beam_id": recovered.get("beam"),
                    "expansion_class": approved_item.get("expansion_class"),
                    "similarity_score": approved_item.get("similarity_score"),
                    "confidence": approved_item.get("confidence"),
                    "recovery_status": "SUCCESS" if bar.get("bar_id") else "NORMALIZATION_PENDING",
                    "original_rejection_reason": recovered.get("original_suppression_reason"),
                    "recovery_reason": recovered.get("recovery_justification"),
                    "expansion_phase": "Phase J.2",
                }
            )
        return entries, counters

    @staticmethod
    def to_recovery_decisions(approved: List[dict[str, Any]]) -> List[dict[str, Any]]:
        recovery_decisions: List[dict[str, Any]] = []
        for item in approved:
            recovery_decisions.append(
                {
                    "discovery_id": item.get("discovery_id"),
                    "recover": True,
                    "recovery_status": "APPROVED",
                    "confidence_score": item.get("confidence") or item.get("similarity_score"),
                    "legitimacy_class": item.get("expansion_class"),
                    "primary_rejection_code": item.get("primary_rejection_code"),
                    "approval_reasons": item.get("approval_reasons") or [],
                    "blocking_reasons": [],
                    "recovery_reason": item.get("recovery_reason"),
                    "beam_id": item.get("beam_id"),
                    "inventory": item.get("inventory") or {},
                    "decision": item.get("decision_record") or {},
                    "audit": {},
                    "legitimacy": {},
                }
            )
        return recovery_decisions
