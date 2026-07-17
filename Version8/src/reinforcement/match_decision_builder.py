"""Build match decisions from ranked beam match candidates."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from loguru import logger

from src.reinforcement.match_decision import (
    CANDIDATE_REASON_TO_DECISION,
    DECISION_STATUS_PENDING_VALIDATION,
    ENGINEERING_STATUS_PRE_MATCH,
    MatchDecision,
    REASON_NO_MATCH,
    format_match_decision_id,
    requires_manual_review,
)


class MatchDecisionBuilder:
    """Create one MatchDecision per DetailIdentity from ranked candidates."""

    def build(
        self,
        drawing_set_id: str,
        floor_id: str,
        drawing_id: str,
        identities: List[dict[str, Any]],
        candidates: List[dict[str, Any]],
    ) -> Tuple[List[dict[str, Any]], List[dict[str, Any]], List[dict[str, Any]]]:
        by_identity: Dict[str, List[dict[str, Any]]] = {}
        for cand in candidates:
            iid = str(cand.get("detail_identity_id", ""))
            by_identity.setdefault(iid, []).append(cand)

        decisions: List[dict[str, Any]] = []
        relationships: List[dict[str, Any]] = []
        updated_identities: List[dict[str, Any]] = []

        for identity in identities:
            iid = str(identity.get("detail_identity_id", ""))
            decision_id = format_match_decision_id(iid)
            candidate_ids = list(identity.get("candidate_ids", []))
            recommended_id = identity.get("best_candidate_id")
            identity_candidates = by_identity.get(iid, [])

            recommended = next(
                (c for c in identity_candidates if c.get("candidate_id") == recommended_id),
                None,
            )
            if recommended is None and identity_candidates:
                recommended = min(
                    identity_candidates,
                    key=lambda c: c.get("metadata", {}).get("rank", 99),
                )
                recommended_id = recommended.get("candidate_id")

            if recommended:
                confidence = float(recommended.get("confidence", 0.0))
                decision_reason = CANDIDATE_REASON_TO_DECISION.get(
                    str(recommended.get("matching_reason", "")),
                    REASON_NO_MATCH,
                )
                recommended_beam = str(recommended.get("beam_context_id", ""))
            else:
                confidence = 0.0
                decision_reason = REASON_NO_MATCH
                recommended_id = None
                recommended_beam = None

            decision = MatchDecision(
                decision_id=decision_id,
                detail_identity_id=iid,
                drawing_set_id=drawing_set_id,
                floor_id=floor_id,
                candidate_count=len(candidate_ids),
                candidate_ids=candidate_ids,
                recommended_candidate_id=recommended_id,
                recommended_beam_context_id=recommended_beam,
                decision_status=DECISION_STATUS_PENDING_VALIDATION,
                decision_reason=decision_reason,
                requires_manual_review=requires_manual_review(confidence),
                confidence=confidence,
                engineering_status=ENGINEERING_STATUS_PRE_MATCH,
                metadata={"drawing_id": drawing_id},
            )
            decision_dict = decision.to_dict()
            decisions.append(decision_dict)

            relationships.append(
                self._rel(iid, decision_id, "DETAIL_HAS_MATCH_DECISION")
            )
            if recommended_id:
                relationships.append(
                    self._rel(decision_id, recommended_id, "MATCH_DECISION_RECOMMENDS_CANDIDATE")
                )
            relationships.append(
                self._rel(decision_id, drawing_set_id, "MATCH_DECISION_BELONGS_TO_DRAWING_SET")
            )

            ident_copy = dict(identity)
            ident_copy["match_decision_id"] = decision_id
            ident_copy["decision_status"] = DECISION_STATUS_PENDING_VALIDATION
            updated_identities.append(ident_copy)

        logger.info(
            "Match decisions built — drawing={} decisions={}",
            drawing_id,
            len(decisions),
        )
        return decisions, updated_identities, relationships

    def _rel(self, source_id: str, target_id: str, relationship: str) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": target_id,
            "relationship": relationship,
            "type": "ENGINEERING",
        }
