"""Registry for engineering detail identities and fingerprints."""

from __future__ import annotations

from typing import Any, List


class DetailIdentityRegistry:
    """Build project-level detail identity and fingerprint registries."""

    @staticmethod
    def build_identities(
        identities: List[dict[str, Any]],
        drawing_id: str = "",
        floor_id: str = "",
    ) -> dict[str, Any]:
        entries = [
            {
                "detail_identity_id": item.get("detail_identity_id"),
                "detail_context_id": item.get("detail_context_id"),
                "detail_type": item.get("detail_type"),
                "primary_beam_mark": item.get("primary_beam_mark"),
                "secondary_beam_marks": item.get("secondary_beam_marks", []),
                "matching_status": item.get("matching_status"),
                "drawing_id": item.get("metadata", {}).get("drawing_id", drawing_id),
            }
            for item in identities
        ]
        return {
            "namespace": "DETAIL",
            "drawing_id": drawing_id,
            "floor_id": floor_id,
            "detail_identity_count": len(entries),
            "detail_identities": entries,
        }

    @staticmethod
    def build_fingerprints(
        fingerprints: List[dict[str, Any]],
        drawing_id: str = "",
        floor_id: str = "",
    ) -> dict[str, Any]:
        entries = [
            {
                "fingerprint_id": fp.get("fingerprint_id"),
                "detail_identity_id": fp.get("detail_identity_id"),
                "overall_hash": fp.get("overall_hash"),
                "entity_count": fp.get("entity_count", 0),
            }
            for fp in fingerprints
        ]
        return {
            "namespace": "FINGERPRINT",
            "drawing_id": drawing_id,
            "floor_id": floor_id,
            "fingerprint_count": len(entries),
            "fingerprints": entries,
        }
