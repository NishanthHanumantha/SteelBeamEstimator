"""Build BeamIndex from beam engineering contexts."""

from __future__ import annotations

from typing import Any, Dict, List

from src.project.beam_index import BeamIndex


class BeamIndexBuilder:
    """Construct beam lookup index for a drawing set."""

    def build(
        self,
        drawing_set_id: str,
        contexts: List[dict[str, Any]],
    ) -> BeamIndex:
        mark_to_context: Dict[str, str] = {}
        contexts_by_id: Dict[str, dict[str, Any]] = {}
        duplicates: List[str] = []

        for ctx in contexts:
            if ctx.get("drawing_set_id") != drawing_set_id:
                continue
            mark = str(ctx.get("beam_mark", "")).upper()
            cid = str(ctx.get("context_id", ""))
            if not mark or not cid:
                continue
            if mark in mark_to_context:
                duplicates.append(mark)
                continue
            mark_to_context[mark] = cid
            contexts_by_id[cid] = ctx

        if duplicates:
            raise ValueError(f"Duplicate beam marks in drawing set {drawing_set_id}: {duplicates}")

        return BeamIndex(drawing_set_id, mark_to_context, contexts_by_id)
