"""BBS trace per annotation."""
from __future__ import annotations
from typing import Dict, List

from .annotation_trace_models import AnnotationTraceRecord


def build_bbs_trace(records: List[AnnotationTraceRecord]) -> Dict:
    return {
        "total": len(records),
        "consumed": sum(1 for r in records if r.bbs_consumed),
        "rows": [
            {"annotation_id": r.annotation_id, "bbs": r.bbs_consumed}
            for r in records
        ],
    }
