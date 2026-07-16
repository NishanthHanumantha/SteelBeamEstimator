"""Diameter trace per annotation."""
from __future__ import annotations
from typing import Dict, List

from .annotation_trace_models import AnnotationTraceRecord


def build_diameter_trace(records: List[AnnotationTraceRecord]) -> Dict:
    buckets = {}
    for r in records:
        if r.diameter_bucket:
            buckets[r.diameter_bucket] = buckets.get(r.diameter_bucket, 0) + 1
    return {
        "total": len(records),
        "with_bucket": sum(1 for r in records if r.diameter_bucket),
        "buckets": buckets,
        "rows": [
            {
                "annotation_id": r.annotation_id,
                "diameter_bucket": r.diameter_bucket,
                "consumed": bool(r.diameter_bucket),
            }
            for r in records
        ],
    }
