"""Engineering bar trace from annotations."""
from __future__ import annotations
from typing import Any, Dict, List

from .annotation_trace_models import AnnotationTraceRecord


def build_engineering_bar_trace(records: List[AnnotationTraceRecord]) -> Dict[str, Any]:
    rows = []
    for r in records:
        rows.append({
            "annotation_id": r.annotation_id,
            "beam_id": r.beam_id,
            "engineering_bar_ids": r.engineering_bar_ids,
            "created": len(r.engineering_bar_ids) > 0,
            "count": len(r.engineering_bar_ids),
        })
    return {"total": len(rows), "rows": rows}
