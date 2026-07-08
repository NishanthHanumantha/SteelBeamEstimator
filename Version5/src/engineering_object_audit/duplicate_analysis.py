"""Analyse duplicate callout collapse into shared engineering bars."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from src.engineering_object_audit.audit_collector import AuditCollector


class DuplicateAnalyzer:
    """Classify valid vs suspicious duplicate callout resolution."""

    def analyze(self, inventory: List[dict[str, Any]], indexes: dict[str, Any]) -> dict[str, Any]:
        groups: Dict[str, List[dict[str, Any]]] = defaultdict(list)
        for item in inventory:
            signature = AuditCollector._inventory_signature(item)
            if signature:
                groups[signature].append(item)

        duplicate_groups: List[dict[str, Any]] = []
        valid_duplicates = 0
        suspicious_duplicates = 0

        for signature, members in groups.items():
            if len(members) < 2:
                continue
            normalized_members = [item for item in members if item.get("normalized_bar_id")]
            rejected_members = [item for item in members if not item.get("normalized_bar_id")]
            shared_bar_ids = sorted({str(item.get("normalized_bar_id")) for item in normalized_members if item.get("normalized_bar_id")})
            duplicate_type = "VALID_DUPLICATE"
            confidence = 0.9
            information_lost = False
            if normalized_members and rejected_members:
                duplicate_type = "SUSPICIOUS_DUPLICATE"
                confidence = 0.75
                information_lost = True
                suspicious_duplicates += 1
            elif len(shared_bar_ids) == 1 and len(normalized_members) > 1:
                duplicate_type = "VALID_DUPLICATE"
                valid_duplicates += 1
            else:
                suspicious_duplicates += 1
                duplicate_type = "SUSPICIOUS_DUPLICATE"
                confidence = 0.6

            duplicate_groups.append(
                {
                    "signature": signature,
                    "member_count": len(members),
                    "normalized_count": len(normalized_members),
                    "rejected_count": len(rejected_members),
                    "shared_bar_ids": shared_bar_ids,
                    "duplicate_type": duplicate_type,
                    "duplicate_confidence": confidence,
                    "information_lost": information_lost,
                    "members": [
                        {
                            "discovery_id": item.get("discovery_id"),
                            "geometry_id": item.get("geometry_id"),
                            "coordinates": item.get("coordinates"),
                            "normalized_bar_id": item.get("normalized_bar_id"),
                        }
                        for item in members
                    ],
                }
            )

        by_discovery: Dict[str, dict[str, Any]] = {}
        for group in duplicate_groups:
            for member in group["members"]:
                by_discovery[member["discovery_id"]] = {
                    "duplicate_type": group["duplicate_type"],
                    "duplicate_confidence": group["duplicate_confidence"],
                    "information_lost": group["information_lost"],
                    "shared_bar_ids": group["shared_bar_ids"],
                    "signature": group["signature"],
                }

        return {
            "duplicate_group_count": len(duplicate_groups),
            "valid_duplicate_groups": valid_duplicates,
            "suspicious_duplicate_groups": suspicious_duplicates,
            "groups": duplicate_groups,
            "by_discovery_id": by_discovery,
        }
