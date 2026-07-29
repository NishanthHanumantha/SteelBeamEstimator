"""Rank beam match candidates deterministically and enrich detail identities."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from loguru import logger

from src.reinforcement.beam_match_candidate import (
    CANDIDATE_STATUS_RANKED,
    MATCHING_STATE_CANDIDATES_READY,
)


class BeamCandidateRanker:
    """Assign ranks to candidates and set identity candidate metadata."""

    def rank(
        self,
        candidates: List[dict[str, Any]],
        identities: List[dict[str, Any]],
    ) -> Tuple[List[dict[str, Any]], List[dict[str, Any]], List[dict[str, Any]]]:
        by_identity: Dict[str, List[dict[str, Any]]] = {}
        for cand in candidates:
            iid = str(cand.get("detail_identity_id", ""))
            by_identity.setdefault(iid, []).append(dict(cand))

        ranked_all: List[dict[str, Any]] = []
        rankings: List[dict[str, Any]] = []
        updated_identities: List[dict[str, Any]] = []

        for identity in identities:
            iid = str(identity.get("detail_identity_id", ""))
            group = by_identity.get(iid, [])
            mark_order = self._mark_order(identity)
            group.sort(
                key=lambda c: (
                    -float(c.get("score", 0)),
                    mark_order.get(str(c.get("beam_mark", "")).upper(), 99),
                    str(c.get("candidate_id", "")),
                )
            )

            ranked_group: List[dict[str, Any]] = []
            for rank, cand in enumerate(group, start=1):
                cand_copy = dict(cand)
                cand_copy["status"] = CANDIDATE_STATUS_RANKED
                meta = dict(cand_copy.get("metadata", {}))
                meta["rank"] = rank
                cand_copy["metadata"] = meta
                ranked_group.append(cand_copy)
                ranked_all.append(cand_copy)

            candidate_ids = [c["candidate_id"] for c in ranked_group]
            best_id = candidate_ids[0] if candidate_ids else None

            ident_copy = dict(identity)
            ident_copy["candidate_count"] = len(candidate_ids)
            ident_copy["candidate_ids"] = candidate_ids
            ident_copy["best_candidate_id"] = best_id
            ident_copy["matching_state"] = MATCHING_STATE_CANDIDATES_READY
            updated_identities.append(ident_copy)

            rankings.append(
                {
                    "detail_identity_id": iid,
                    "best_candidate_id": best_id,
                    "candidate_count": len(candidate_ids),
                    "candidates": [
                        {
                            "candidate_id": c["candidate_id"],
                            "beam_context_id": c.get("beam_context_id"),
                            "beam_mark": c.get("beam_mark"),
                            "rank": c.get("metadata", {}).get("rank"),
                            "score": c.get("score"),
                            "confidence": c.get("confidence"),
                            "matching_reason": c.get("matching_reason"),
                            "status": c.get("status"),
                        }
                        for c in ranked_group
                    ],
                }
            )

        logger.info(
            "Beam candidates ranked — identities={} candidates={}",
            len(updated_identities),
            len(ranked_all),
        )
        return ranked_all, rankings, updated_identities

    def _mark_order(self, identity: dict[str, Any]) -> dict[str, int]:
        primary = str(identity.get("primary_beam_mark", "")).upper()
        secondary = [str(m).upper() for m in identity.get("secondary_beam_marks", [])]
        ordered = [primary] + secondary if primary else secondary
        return {mark: idx for idx, mark in enumerate(ordered)}
