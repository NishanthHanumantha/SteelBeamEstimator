"""Classify missing engineering objects into expansion classes."""

from __future__ import annotations

from typing import Any, Dict, List


class ExpansionClass:
    ALREADY_RECOVERED = "ALREADY_RECOVERED"
    MISSING_NORMALIZATION = "MISSING_NORMALIZATION"
    MISSING_ASSOCIATION = "MISSING_ASSOCIATION"
    MISSING_SPECIFICATION = "MISSING_SPECIFICATION"
    MISSING_CONTEXT = "MISSING_CONTEXT"
    MISSING_GROUP = "MISSING_GROUP"
    PARTIAL_OBJECT = "PARTIAL_OBJECT"
    UNRECOVERABLE = "UNRECOVERABLE"
    UNKNOWN = "UNKNOWN"


UNRECOVERABLE_REJECTION_CODES = frozenset(
    {
        "UNSUPPORTED_NOTATION",
        "AMBIGUOUS_CALLOUT",
        "NOT_REINFORCEMENT",
    }
)


class CandidateClassifier:
    """Assign exactly one expansion class to each gap candidate."""

    def classify(self, gap: dict[str, Any], snapshot: dict[str, Any]) -> str:
        discovery_id = str(gap.get("discovery_id") or "")
        inventory = gap.get("inventory") or {}
        decision = gap.get("decision") or {}
        rejection_code = str(decision.get("primary_rejection_code") or gap.get("primary_rejection_code") or "")

        if discovery_id in set(snapshot.get("expansion_recovered_ids") or []):
            return ExpansionClass.ALREADY_RECOVERED
        if discovery_id in set(snapshot.get("j1_recovered_ids") or []):
            return ExpansionClass.ALREADY_RECOVERED
        if discovery_id in set(snapshot.get("production_discovery_ids") or []):
            return ExpansionClass.ALREADY_RECOVERED

        if rejection_code in UNRECOVERABLE_REJECTION_CODES:
            return ExpansionClass.UNRECOVERABLE
        if inventory.get("ambiguous") or inventory.get("unknown"):
            return ExpansionClass.UNRECOVERABLE
        if not inventory.get("classified"):
            return ExpansionClass.UNRECOVERABLE

        if not inventory.get("associated"):
            return ExpansionClass.MISSING_ASSOCIATION

        beam_id = str(inventory.get("beam_association") or "")
        if not beam_id:
            return ExpansionClass.MISSING_ASSOCIATION
        if beam_id not in (snapshot.get("contexts_by_beam") or {}):
            return ExpansionClass.MISSING_CONTEXT

        if not self._specification_ready(inventory):
            return ExpansionClass.MISSING_SPECIFICATION

        if not inventory.get("geometry_id"):
            return ExpansionClass.MISSING_SPECIFICATION
        coordinates = inventory.get("coordinates") or {}
        if coordinates.get("x") is None or coordinates.get("y") is None:
            return ExpansionClass.PARTIAL_OBJECT

        if rejection_code == "MISSING_GEOMETRY" and inventory.get("geometry_id"):
            return ExpansionClass.MISSING_NORMALIZATION

        if not inventory.get("normalized_bar_id") and not inventory.get("engineering_object_id"):
            if self._specification_ready(inventory) and inventory.get("geometry_id"):
                return ExpansionClass.MISSING_NORMALIZATION

        if self._partial_object(inventory):
            return ExpansionClass.PARTIAL_OBJECT

        return ExpansionClass.UNKNOWN

    @staticmethod
    def _specification_ready(inventory: dict[str, Any]) -> bool:
        return all(
            [
                inventory.get("beam_association"),
                inventory.get("diameter_mm") is not None,
                inventory.get("quantity") is not None,
                inventory.get("role"),
            ]
        )

    @staticmethod
    def _partial_object(inventory: dict[str, Any]) -> bool:
        required = [
            inventory.get("beam_association"),
            inventory.get("role"),
            inventory.get("diameter_mm"),
            inventory.get("quantity"),
            inventory.get("geometry_id"),
        ]
        present = sum(1 for value in required if value not in (None, ""))
        return 0 < present < len(required)
