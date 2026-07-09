"""Create BeamMatch objects from validated match decisions."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from loguru import logger

from src.reinforcement.beam_match import (
    EXECUTION_STATUS_EXECUTED,
    EXECUTION_STATUS_NOT_EXECUTED,
    BeamMatch,
    decision_eligible_for_match,
    format_beam_match_id,
)
from src.reinforcement.detail_identity import (
    MATCHING_STATE_MATCH_COMPLETED,
    MATCHING_STATUS_MATCHED,
)
from src.reinforcement.match_decision_quality import ALGORITHM_VERSION


class BeamMatchBuilder:
    """Commit ENGINEERING_READY decisions into authoritative BeamMatch relationships."""

    def build(
        self,
        model: dict[str, Any],
        drawing_set_id: str,
        floor_id: str,
        drawing_id: str,
        identities: List[dict[str, Any]],
        decisions: List[dict[str, Any]],
        candidates: List[dict[str, Any]],
    ) -> Tuple[
        List[dict[str, Any]],
        List[dict[str, Any]],
        List[dict[str, Any]],
        List[dict[str, Any]],
        List[dict[str, Any]],
    ]:
        project_id = str(model.get("project_workspace", {}).get("project_id", ""))
        candidate_by_id = {str(c.get("candidate_id")): c for c in candidates}
        context_by_id = {
            str(ctx.get("context_id")): ctx
            for ctx in model.get("beam_engineering_contexts", [])
        }
        identity_by_id = {str(i.get("detail_identity_id")): i for i in identities}

        matches: List[dict[str, Any]] = []
        relationships: List[dict[str, Any]] = []
        updated_decisions: List[dict[str, Any]] = []

        for decision in decisions:
            decision_copy = dict(decision)
            iid = str(decision.get("detail_identity_id", ""))
            identity = identity_by_id.get(iid, {})
            ctx_id = str(identity.get("detail_context_id", ""))

            if decision_eligible_for_match(decision):
                recommended_id = str(decision.get("recommended_candidate_id", ""))
                recommended = candidate_by_id.get(recommended_id, {})
                beam_context_id = str(
                    decision.get("recommended_beam_context_id")
                    or recommended.get("beam_context_id", "")
                )
                beam_mark = str(recommended.get("beam_mark", ""))
                if not beam_mark and beam_context_id:
                    beam_mark = str(
                        context_by_id.get(beam_context_id, {}).get("beam_mark", "")
                    )

                beam_match = BeamMatch(
                    beam_match_id=format_beam_match_id(iid),
                    detail_identity_id=iid,
                    detail_context_id=ctx_id,
                    match_decision_id=str(decision.get("decision_id", "")),
                    beam_context_id=beam_context_id,
                    beam_mark=beam_mark,
                    drawing_set_id=drawing_set_id,
                    project_id=project_id or str(recommended.get("project_id", "")),
                    floor_id=floor_id,
                    confidence=float(decision.get("confidence", 0.0)),
                    confidence_level=str(decision.get("confidence_level", "")),
                    algorithm_version=str(
                        decision.get("algorithm_info", {}).get(
                            "algorithm_version", ALGORITHM_VERSION
                        )
                    ),
                    metadata={"drawing_id": drawing_id},
                )
                match_dict = beam_match.to_dict()
                matches.append(match_dict)

                relationships.append(
                    self._rel(iid, match_dict["beam_match_id"], "DETAIL_MATCHED_TO")
                )
                relationships.append(
                    self._rel(
                        match_dict["beam_match_id"],
                        match_dict["match_decision_id"],
                        "BEAM_MATCH_REFERENCES",
                    )
                )
                relationships.append(
                    self._rel(
                        match_dict["beam_match_id"],
                        beam_context_id,
                        "BEAM_MATCH_TARGETS",
                    )
                )
                relationships.append(
                    self._rel(
                        beam_context_id,
                        match_dict["beam_match_id"],
                        "BEAM_CONTEXT_HAS_REINFORCEMENT_MATCH",
                    )
                )

                if beam_context_id in context_by_id:
                    ctx_copy = dict(context_by_id[beam_context_id])
                    ctx_copy["beam_match_id"] = match_dict["beam_match_id"]
                    ctx_copy["reinforcement_context_id"] = ctx_id
                    ctx_copy["reinforcement_matching_status"] = MATCHING_STATUS_MATCHED
                    if drawing_id:
                        ctx_copy["reinforcement_drawing_id"] = drawing_id
                    context_by_id[beam_context_id] = ctx_copy

                decision_copy["execution_status"] = EXECUTION_STATUS_EXECUTED
            else:
                decision_copy["execution_status"] = EXECUTION_STATUS_NOT_EXECUTED

            updated_decisions.append(decision_copy)

        match_by_identity = {m["detail_identity_id"]: m for m in matches}
        updated_identities: List[dict[str, Any]] = []
        for identity in identities:
            ident_copy = dict(identity)
            iid = str(identity.get("detail_identity_id", ""))
            match = match_by_identity.get(iid)
            if match:
                ident_copy["beam_match_id"] = match["beam_match_id"]
                ident_copy["matching_status"] = MATCHING_STATUS_MATCHED
                ident_copy["matching_state"] = MATCHING_STATE_MATCH_COMPLETED
            updated_identities.append(ident_copy)

        model["beam_engineering_contexts"] = list(context_by_id.values())

        logger.info(
            "Beam matches built — drawing={} matches={} executed={}",
            drawing_id,
            len(matches),
            sum(
                1
                for d in updated_decisions
                if d.get("execution_status") == EXECUTION_STATUS_EXECUTED
            ),
        )
        return (
            matches,
            updated_identities,
            updated_decisions,
            list(context_by_id.values()),
            relationships,
        )

    def _rel(self, source_id: str, target_id: str, relationship: str) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": target_id,
            "relationship": relationship,
            "type": "ENGINEERING",
        }
