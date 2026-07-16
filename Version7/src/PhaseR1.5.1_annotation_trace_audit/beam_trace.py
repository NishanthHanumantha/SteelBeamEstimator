"""Beam-level annotation trace."""
from __future__ import annotations
from typing import Dict, List

from .annotation_trace_models import AnnotationTraceRecord


def build_beam_trace(records: List[AnnotationTraceRecord]) -> Dict:
    by_beam = {}
    for r in records:
        by_beam.setdefault(r.beam_id, []).append(r.to_dict())
    return {
        "beam_count": len(by_beam),
        "beams": {
            bid: {
                "annotations": len(rows),
                "consumed": sum(1 for x in rows if x.get("status") == "CONSUMED"),
                "lost": sum(1 for x in rows if x.get("status") == "LOST"),
            }
            for bid, rows in by_beam.items()
        },
    }
