"""Forensic audit statistics."""
from __future__ import annotations
from typing import Any, Dict, List

from .annotation_trace_models import AnnotationTraceRecord


class AnnotationStatistics:

    def compute(
        self,
        records: List[AnnotationTraceRecord],
        losses: Dict[str, Any],
        dxf_y10: List[Dict],
        loader: Any,
    ) -> Dict[str, Any]:
        y10_recs = [
            r for r in records
            if r.diameter_mm == 10
            or "Y10" in r.normalized_text.upper()
            or r.role == "Y10_CANDIDATE"
        ]
        stirrup_recs = [r for r in records if r.role == "STIRRUP"]
        spacer_recs = [r for r in records if r.role == "SPACER_BAR"]

        dia_summary = loader.steel_json.get("diameter_summary", [])
        y10_steel = next(
            (d for d in dia_summary if d.get("diameter_mm") == 10), None
        )

        return {
            "total_annotations": len(records),
            "discovered_annotations": sum(
                1 for r in records if not r.annotation_id.startswith("DXF_")
            ),
            "dxf_forensic_only": sum(
                1 for r in records if r.annotation_id.startswith("DXF_")
            ),
            "grouped": sum(1 for r in records if r.group_id),
            "engineering_bars": sum(len(r.engineering_bar_ids) for r in records),
            "steel": sum(1 for r in records if r.steel_consumed),
            "bbs": sum(1 for r in records if r.bbs_consumed),
            "diameter": sum(1 for r in records if r.diameter_bucket),
            "excel": sum(1 for r in records if r.excel_reached),
            "lost": losses.get("lost", 0),
            "merged": losses.get("merged", 0),
            "expanded": losses.get("expanded", 0),
            "y10": {
                "dxf_entities": len(dxf_y10),
                "pipeline_annotations": len(y10_recs),
                "consumed": sum(1 for r in y10_recs if r.status == "CONSUMED"),
                "lost": sum(1 for r in y10_recs if r.status == "LOST"),
                "engineering_bars": sum(
                    len(r.engineering_bar_ids) for r in y10_recs
                ),
                "steel_in_diameter_summary": y10_steel,
            },
            "stirrup": {
                "total": len(stirrup_recs),
                "consumed": sum(1 for r in stirrup_recs if r.steel_consumed),
                "lost": sum(1 for r in stirrup_recs if r.status == "LOST"),
            },
            "spacer": {
                "total": len(spacer_recs),
                "consumed": sum(1 for r in spacer_recs if r.steel_consumed),
                "lost": sum(1 for r in spacer_recs if r.status == "LOST"),
            },
        }
