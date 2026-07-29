"""Generate beam match candidates from detail identities and drawing-set beam index."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from loguru import logger

from src.project.beam_index import BeamIndex
from src.project.beam_index_builder import BeamIndexBuilder
from src.reinforcement.beam_match_candidate import (
    ALGORITHM_CONTINUOUS_SPAN_MATCH,
    ALGORITHM_DIRECT_LABEL_MATCH,
    ALGORITHM_MULTI_VIEW_MATCH,
    BeamMatchCandidate,
    CANDIDATE_STATUS_GENERATED,
    REASON_CONTINUOUS_MULTI_SPAN,
    REASON_DIRECT_BEAM_MARK,
    REASON_MULTI_VIEW_SINGLE_BEAM,
    SCORE_CONTINUOUS_MULTI_SPAN,
    SCORE_DIRECT_BEAM_MARK,
    SCORE_MULTI_VIEW,
    format_candidate_id,
)
from src.reinforcement.detail_context import (
    DETAIL_TYPE_CONTINUOUS_MULTI_SPAN,
    DETAIL_TYPE_MULTI_VIEW_SINGLE_BEAM,
)


class BeamCandidateBuilder:
    """Build candidate beams from detail marks within the same drawing set and floor."""

    def build(
        self,
        model: dict[str, Any],
        drawing_id: str,
        drawing_set_id: str,
        floor_id: str,
        identities: List[dict[str, Any]],
    ) -> Tuple[List[dict[str, Any]], List[dict[str, Any]]]:
        beam_index = self._beam_index_for_set(model, drawing_set_id, floor_id)
        candidates: List[dict[str, Any]] = []
        relationships: List[dict[str, Any]] = []

        for identity in identities:
            detail_identity_id = str(identity.get("detail_identity_id", ""))
            detail_type = str(identity.get("detail_type", ""))
            marks = self._marks_for_identity(identity)
            score, reason, algorithm = self._scoring_for_type(detail_type)

            for mark in marks:
                beam_ctx = beam_index.get_beam_context(mark)
                if not beam_ctx:
                    continue
                if beam_ctx.get("drawing_set_id") != drawing_set_id:
                    continue
                if beam_ctx.get("floor_id") != floor_id:
                    continue

                candidate = BeamMatchCandidate(
                    candidate_id=format_candidate_id(detail_identity_id, mark),
                    detail_identity_id=detail_identity_id,
                    beam_context_id=str(beam_ctx.get("context_id", "")),
                    beam_mark=mark.upper(),
                    drawing_set_id=drawing_set_id,
                    floor_id=floor_id,
                    project_id=str(beam_ctx.get("project_id", "")),
                    confidence=score,
                    score=score,
                    matching_algorithm=algorithm,
                    matching_reason=reason,
                    status=CANDIDATE_STATUS_GENERATED,
                    metadata={
                        "drawing_id": drawing_id,
                        "detail_type": detail_type,
                    },
                )
                cand_dict = candidate.to_dict()
                candidates.append(cand_dict)
                relationships.append(
                    self._rel(detail_identity_id, cand_dict["candidate_id"], "DETAIL_HAS_CANDIDATE")
                )
                relationships.append(
                    self._rel(
                        cand_dict["candidate_id"],
                        cand_dict["beam_context_id"],
                        "CANDIDATE_TARGETS_CONTEXT",
                    )
                )

        logger.info(
            "Beam candidates built — drawing={} candidates={}",
            drawing_id,
            len(candidates),
        )
        return candidates, relationships

    def _beam_index_for_set(
        self,
        model: dict[str, Any],
        drawing_set_id: str,
        floor_id: str,
    ) -> BeamIndex:
        contexts = [
            ctx
            for ctx in model.get("beam_engineering_contexts", [])
            if ctx.get("drawing_set_id") == drawing_set_id
            and ctx.get("floor_id") == floor_id
        ]
        return BeamIndexBuilder().build(drawing_set_id, contexts)

    def _marks_for_identity(self, identity: dict[str, Any]) -> List[str]:
        detail_type = str(identity.get("detail_type", ""))
        primary = str(identity.get("primary_beam_mark", "")).upper()
        secondary = [str(m).upper() for m in identity.get("secondary_beam_marks", [])]

        if detail_type == DETAIL_TYPE_CONTINUOUS_MULTI_SPAN:
            marks = [primary] + secondary if primary else secondary
        elif detail_type == DETAIL_TYPE_MULTI_VIEW_SINGLE_BEAM:
            marks = [primary] if primary else []
        else:
            marks = [primary] if primary else []

        return [m for m in marks if m]

    def _scoring_for_type(self, detail_type: str) -> Tuple[float, str, str]:
        if detail_type == DETAIL_TYPE_CONTINUOUS_MULTI_SPAN:
            return (
                SCORE_CONTINUOUS_MULTI_SPAN,
                REASON_CONTINUOUS_MULTI_SPAN,
                ALGORITHM_CONTINUOUS_SPAN_MATCH,
            )
        if detail_type == DETAIL_TYPE_MULTI_VIEW_SINGLE_BEAM:
            return (
                SCORE_MULTI_VIEW,
                REASON_MULTI_VIEW_SINGLE_BEAM,
                ALGORITHM_MULTI_VIEW_MATCH,
            )
        return (
            SCORE_DIRECT_BEAM_MARK,
            REASON_DIRECT_BEAM_MARK,
            ALGORITHM_DIRECT_LABEL_MATCH,
        )

    def _rel(self, source_id: str, target_id: str, relationship: str) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": target_id,
            "relationship": relationship,
            "type": "ENGINEERING",
        }
