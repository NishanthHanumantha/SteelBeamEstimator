"""Steel consumption trace per annotation."""
from __future__ import annotations
from typing import Dict, List

from .annotation_trace_models import AnnotationTraceRecord


def build_steel_trace(records: List[AnnotationTraceRecord]) -> Dict:
    return {
        "total": len(records),
        "consumed": sum(1 for r in records if r.steel_consumed),
        "skipped": sum(1 for r in records if not r.steel_consumed),
        "rows": [
            {
                "annotation_id": r.annotation_id,
                "beam_id": r.beam_id,
                "consumed": r.steel_consumed,
                "root_cause": r.root_cause if not r.steel_consumed else "",
            }
            for r in records
        ],
    }
