"""Annotation group trace export."""
from __future__ import annotations
from typing import Any, Dict, List

from .annotation_trace_models import AnnotationTraceRecord


def build_group_trace(records: List[AnnotationTraceRecord]) -> Dict[str, Any]:
    rows = []
    for r in records:
        rows.append({
            "annotation_id": r.annotation_id,
            "beam_id": r.beam_id,
            "role": r.role,
            "group_id": r.group_id,
            "merged": r.group_merged,
            "expanded": r.group_expanded,
            "status": "GROUPED" if r.group_id else "NO_GROUP",
        })
    return {"total": len(rows), "rows": rows}
