"""Conflict detection for property resolution — Phase G.5.3.2."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.property_parser.property_parser_types import PARSE_STATUS_PARSED
from src.property_resolver.resolution_strategy import normalize_value_key


class PropertyConflictDetector:
    """Detect conflicting parsed values within a property group."""

    @staticmethod
    def detect_group_conflict(
        engineering_object_id: str,
        property_type: str,
        group: List[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        parsed = [p for p in group if p.get("parse_status") == PARSE_STATUS_PARSED]
        if len(parsed) < 2:
            return None

        value_groups: Dict[str, List[dict[str, Any]]] = {}
        for prop in parsed:
            key = normalize_value_key(prop)
            if not key:
                continue
            value_groups.setdefault(key, []).append(prop)

        if len(value_groups) <= 1:
            return None

        conflicting_values = sorted(value_groups.keys())
        property_ids = [str(p.get("property_id", "")) for p in parsed if p.get("property_id")]
        candidate_ids = sorted(
            {str(p.get("candidate_id", "")) for p in parsed if p.get("candidate_id")}
        )
        return {
            "engineering_object_id": engineering_object_id,
            "property_type": property_type,
            "conflicting_values": conflicting_values,
            "property_ids": property_ids,
            "candidate_ids": candidate_ids,
            "property_count": len(parsed),
            "distinct_value_count": len(conflicting_values),
        }

    @staticmethod
    def detect_all_conflicts(
        grouped: Dict[tuple[str, str], List[dict[str, Any]]],
    ) -> List[dict[str, Any]]:
        conflicts: List[dict[str, Any]] = []
        for (obj_id, ptype), group in sorted(grouped.items()):
            conflict = PropertyConflictDetector.detect_group_conflict(obj_id, ptype, group)
            if conflict:
                conflicts.append(conflict)
        return conflicts
