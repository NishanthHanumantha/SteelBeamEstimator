"""Build Engineering Detail Contexts from G.2.2 region and view outputs."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from loguru import logger

from src.reinforcement.detail_context import (
    DETAIL_TYPE_UNKNOWN,
    EngineeringDetailContext,
    detail_context_id_from_region,
)


class DetailContextBuilder:
    """Convert classified regions into engineering detail contexts (1:1 for now)."""

    def build(
        self,
        drawing_id: str,
        regions: List[dict[str, Any]],
        detail_views: List[dict[str, Any]],
    ) -> Tuple[List[dict[str, Any]], List[dict[str, Any]], List[dict[str, Any]], List[dict[str, Any]]]:
        contexts: List[dict[str, Any]] = []
        updated_regions: List[dict[str, Any]] = []
        relationships: List[dict[str, Any]] = []
        ctx_by_region: Dict[str, str] = {}

        views_by_region: Dict[str, List[dict[str, Any]]] = {}
        for view in detail_views:
            rid = str(view.get("region_id", ""))
            views_by_region.setdefault(rid, []).append(view)

        for idx, region in enumerate(regions, start=1):
            region_id = str(region.get("geometry_id", ""))
            ctx_id = detail_context_id_from_region(region_id, idx)
            view_ids = list(region.get("views", []))
            if not view_ids:
                view_ids = [
                    str(v.get("view_id", v.get("geometry_id", "")))
                    for v in views_by_region.get(region_id, [])
                ]

            detail_type = str(region.get("detail_type", DETAIL_TYPE_UNKNOWN))
            beam_marks = list(region.get("beam_marks", []))
            beam_count = int(region.get("beam_count", len(set(beam_marks))))
            view_count = int(region.get("view_count", len(view_ids)))
            confidence = float(region.get("engineering_confidence", 1.0))

            context = EngineeringDetailContext(
                detail_context_id=ctx_id,
                detail_type=detail_type,
                region_id=region_id,
                view_ids=view_ids,
                beam_marks=beam_marks,
                beam_count=beam_count,
                view_count=view_count,
                confidence=confidence,
                metadata={
                    "drawing_id": drawing_id,
                    "region_label": region.get("label", ""),
                    "duplicate_mark_detected": bool(region.get("duplicate_mark_detected", False)),
                },
            )
            contexts.append(context.to_dict())
            ctx_by_region[region_id] = ctx_id

            region_copy = dict(region)
            region_copy["detail_context_ids"] = [ctx_id]
            updated_regions.append(region_copy)

            relationships.append(
                self._rel(region_id, ctx_id, "REGION_HAS_DETAIL_CONTEXT")
            )
            relationships.append(
                self._rel(ctx_id, drawing_id, "DETAIL_CONTEXT_BELONGS_TO_DRAWING")
            )
            for view_id in view_ids:
                relationships.append(
                    self._rel(ctx_id, view_id, "DETAIL_CONTEXT_HAS_VIEW")
                )

        updated_views: List[dict[str, Any]] = []
        for view in detail_views:
            view_copy = dict(view)
            rid = str(view.get("region_id", ""))
            if rid in ctx_by_region:
                view_copy["detail_context_id"] = ctx_by_region[rid]
            updated_views.append(view_copy)

        logger.info(
            "Detail contexts built — drawing={} contexts={} regions={} views={}",
            drawing_id,
            len(contexts),
            len(updated_regions),
            len(updated_views),
        )
        return contexts, updated_regions, updated_views, relationships

    def _rel(self, source_id: str, target_id: str, relationship: str) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": target_id,
            "relationship": relationship,
            "type": "ENGINEERING",
        }
