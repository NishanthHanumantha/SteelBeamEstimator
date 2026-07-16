"""Annotation loss detection and root cause aggregation."""
from __future__ import annotations
from collections import Counter
from typing import Any, Dict, List

from .annotation_trace_models import AnnotationTraceRecord


class AnnotationLossDetector:

    def detect(self, records: List[AnnotationTraceRecord]) -> Dict[str, Any]:
        lost = [r for r in records if r.status in ("LOST", "IGNORED")]
        consumed = [r for r in records if r.status == "CONSUMED"]
        partial = [r for r in records if r.status == "PARTIAL"]
        merged = [r for r in records if r.group_merged]
        expanded = [r for r in records if r.group_expanded]

        stage_loss = Counter(r.first_loss_stage for r in lost if r.first_loss_stage)
        root_causes = Counter(r.root_cause for r in records if r.root_cause)

        return {
            "total_annotations": len(records),
            "consumed": len(consumed),
            "partial": len(partial),
            "lost": len(lost),
            "ignored": sum(1 for r in records if r.status == "IGNORED"),
            "merged": len(merged),
            "expanded": len(expanded),
            "lost_by_stage": dict(stage_loss),
            "root_cause_counts": dict(root_causes),
            "lost_records": [r.to_dict() for r in lost],
        }
