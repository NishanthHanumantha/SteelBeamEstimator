"""Build Engineering Detail Identities from DetailContexts."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from loguru import logger

from src.reinforcement.detail_identity import (
    MATCHING_STATUS_NOT_MATCHED,
    SOURCE_DETAIL_CONTEXT,
    EngineeringDetailIdentity,
    detail_identity_id_from_context,
    split_beam_marks,
)


class DetailIdentityBuilder:
    """Create one DetailIdentity per DetailContext (1:1, no merge/split)."""

    def build(
        self,
        drawing_id: str,
        contexts: List[dict[str, Any]],
    ) -> Tuple[List[dict[str, Any]], List[dict[str, Any]], List[dict[str, Any]]]:
        identities: List[dict[str, Any]] = []
        updated_contexts: List[dict[str, Any]] = []
        relationships: List[dict[str, Any]] = []

        for idx, ctx in enumerate(contexts, start=1):
            ctx_id = str(ctx.get("detail_context_id", ""))
            identity_id = detail_identity_id_from_context(ctx_id, idx)
            beam_marks = list(ctx.get("beam_marks", []))
            primary, secondary = split_beam_marks(beam_marks)

            identity = EngineeringDetailIdentity(
                detail_identity_id=identity_id,
                detail_context_id=ctx_id,
                detail_type=str(ctx.get("detail_type", "UNKNOWN")),
                primary_beam_mark=primary,
                secondary_beam_marks=secondary,
                beam_count=int(ctx.get("beam_count", len(beam_marks))),
                view_count=int(ctx.get("view_count", len(ctx.get("view_ids", [])))),
                matching_status=MATCHING_STATUS_NOT_MATCHED,
                engineering_owner=None,
                confidence=float(ctx.get("confidence", 1.0)),
                source=SOURCE_DETAIL_CONTEXT,
                metadata={
                    "drawing_id": drawing_id,
                    "region_id": ctx.get("region_id", ""),
                    "view_ids": list(ctx.get("view_ids", [])),
                    "beam_marks": beam_marks,
                },
            )
            identities.append(identity.to_dict())

            ctx_copy = dict(ctx)
            ctx_copy["detail_identity_id"] = identity_id
            updated_contexts.append(ctx_copy)

            relationships.append(
                self._rel(ctx_id, identity_id, "DETAIL_CONTEXT_HAS_DETAIL")
            )
            relationships.append(
                self._rel(identity_id, drawing_id, "DETAIL_BELONGS_TO_DRAWING")
            )

        logger.info(
            "Detail identities built — drawing={} identities={}",
            drawing_id,
            len(identities),
        )
        return identities, updated_contexts, relationships

    def _rel(self, source_id: str, target_id: str, relationship: str) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": target_id,
            "relationship": relationship,
            "type": "ENGINEERING",
        }
