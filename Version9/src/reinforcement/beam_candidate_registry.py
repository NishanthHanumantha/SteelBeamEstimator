"""Registry export for beam match candidates."""

from __future__ import annotations

from typing import Any, List


class BeamCandidateRegistry:
    """Build project-level beam candidate registry."""

    @staticmethod
    def build(
        candidates: List[dict[str, Any]],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
    ) -> dict[str, Any]:
        entries = [
            {
                "candidate_id": item.get("candidate_id"),
                "detail_identity_id": item.get("detail_identity_id"),
                "beam_context_id": item.get("beam_context_id"),
                "beam_mark": item.get("beam_mark"),
                "score": item.get("score"),
                "confidence": item.get("confidence"),
                "matching_reason": item.get("matching_reason"),
                "status": item.get("status"),
                "rank": item.get("metadata", {}).get("rank"),
            }
            for item in candidates
        ]
        return {
            "namespace": "MATCH_CANDIDATE",
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "candidate_count": len(entries),
            "candidates": entries,
        }
