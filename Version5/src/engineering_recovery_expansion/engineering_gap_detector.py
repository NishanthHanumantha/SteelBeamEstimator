"""Deterministically identify engineering objects missing from production."""

from __future__ import annotations

from typing import Any, Dict, List


class EngineeringGapDetector:
    """Identify discovery objects absent from production registries."""

    @staticmethod
    def detect(snapshot: dict[str, Any]) -> dict[str, Any]:
        inventory = snapshot.get("inventory") or []
        inventory_by_id = snapshot.get("inventory_by_id") or {}
        decision_by_id = snapshot.get("decision_by_id") or {}
        existing_objects = snapshot.get("existing_objects") or []
        existing_specs = snapshot.get("existing_specs") or []
        existing_contexts = snapshot.get("existing_contexts") or []
        existing_bars = snapshot.get("existing_bars") or []
        existing_groups = snapshot.get("existing_groups") or []
        already_recovered = set(snapshot.get("already_recovered_ids") or [])
        j1_recovered = set(snapshot.get("j1_recovered_ids") or [])
        expansion_recovered = set(snapshot.get("expansion_recovered_ids") or [])

        production_object_ids = {
            str(item.get("engineering_object_id") or item.get("object_id"))
            for item in existing_objects
            if item.get("engineering_object_id") or item.get("object_id")
        }
        production_spec_ids = {
            str(item.get("specification_id")) for item in existing_specs if item.get("specification_id")
        }
        production_context_ids = {
            str(item.get("context_id")) for item in existing_contexts if item.get("context_id")
        }
        production_bar_ids = {str(item.get("bar_id")) for item in existing_bars if item.get("bar_id")}
        production_group_ids = {str(item.get("group_id")) for item in existing_groups if item.get("group_id")}

        missing_normalized: List[dict[str, Any]] = []
        missing_specifications: List[dict[str, Any]] = []
        missing_contexts: List[dict[str, Any]] = []
        missing_groups: List[dict[str, Any]] = []
        missing_beam_associations: List[dict[str, Any]] = []
        missing_geometry_links: List[dict[str, Any]] = []

        for item in inventory:
            discovery_id = str(item.get("discovery_id") or "")
            if not discovery_id:
                continue
            if item.get("engineering_object_id") and item.get("normalized_bar_id"):
                continue
            if discovery_id in j1_recovered:
                continue

            decision = decision_by_id.get(discovery_id, {})
            gap_record = {
                "discovery_id": discovery_id,
                "inventory": item,
                "decision": decision,
                "primary_rejection_code": decision.get("primary_rejection_code"),
                "beam_id": item.get("beam_association"),
                "geometry_id": item.get("geometry_id"),
                "engineering_object_id": item.get("engineering_object_id"),
                "normalized_bar_id": item.get("normalized_bar_id"),
            }

            if not item.get("normalized_bar_id"):
                missing_normalized.append(gap_record)
            if not item.get("engineering_object_id"):
                missing_specifications.append(gap_record)
            if not item.get("beam_association"):
                missing_beam_associations.append(gap_record)
            if not item.get("geometry_id"):
                missing_geometry_links.append(gap_record)
            elif not (item.get("coordinates") or {}).get("x") or (item.get("coordinates") or {}).get("y") is None:
                if decision.get("primary_rejection_code") == "MISSING_GEOMETRY":
                    missing_geometry_links.append(gap_record)

            beam_id = str(item.get("beam_association") or "")
            if beam_id and beam_id not in (snapshot.get("contexts_by_beam") or {}):
                missing_contexts.append(gap_record)

        return {
            "missing_normalized_objects": missing_normalized,
            "missing_specifications": missing_specifications,
            "missing_calculation_contexts": missing_contexts,
            "missing_reinforcement_groups": missing_groups,
            "missing_beam_associations": missing_beam_associations,
            "missing_geometry_links": missing_geometry_links,
            "production_object_ids": sorted(production_object_ids),
            "production_specification_ids": sorted(production_spec_ids),
            "production_context_ids": sorted(production_context_ids),
            "production_bar_ids": sorted(production_bar_ids),
            "production_group_ids": sorted(production_group_ids),
            "candidate_pool": EngineeringGapDetector._unique_gaps(missing_normalized),
            "inventory_by_id": inventory_by_id,
        }

    @staticmethod
    def _unique_gaps(records: List[dict[str, Any]]) -> List[dict[str, Any]]:
        seen: set[str] = set()
        unique: List[dict[str, Any]] = []
        for record in sorted(records, key=lambda item: str(item.get("discovery_id"))):
            discovery_id = str(record.get("discovery_id") or "")
            if discovery_id in seen:
                continue
            seen.add(discovery_id)
            unique.append(record)
        return unique
