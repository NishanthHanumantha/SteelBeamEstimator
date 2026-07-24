"""
Engineering review dataset builder — blanks left for manual completion.
MODEL_VERSION: 8.8.3
"""
from __future__ import annotations

from typing import Any, Dict, List

from beam_analysis_model import BeamAnalysisRecord, MODEL_VERSION
from input_loader import natural_beam_key


class EngineeringReviewBuilder:
    def build(self, records: List[BeamAnalysisRecord]) -> Dict[str, Any]:
        rows: List[Dict[str, Any]] = []
        for r in sorted(records, key=lambda x: natural_beam_key(x.inventory.beam_id)):
            st = r.stirrup_status
            ev = r.drawing_evidence
            evidence_summary = (
                f"annotations={ev.annotation_count}; "
                f"roles={ev.role_counts}; "
                f"leaders_near={ev.leader_count_near_beam}; "
                f"unknown_texts={ev.unknown_annotation_texts[:5]}; "
                f"pipeline={[s.status for s in r.pipeline_trace]}"
            )
            rows.append({
                "beam_id": r.inventory.beam_id,
                "detected": st.stirrup_detected,
                "detected_notation": st.detected_notation,
                "detected_diameter_mm": st.detected_diameter_mm,
                "spacing_mm": st.spacing_mm,
                "leg_count": st.leg_count,
                "drawing_file": r.inventory.drawing_name,
                "drawing_path": r.inventory.drawing_path,
                "rule012_status": r.rule012_status,
                "evidence_summary": evidence_summary,
                "engineering_comments": "",
                "estimator_comments": "",
                "root_cause": "",
                "status": "OPEN",
            })
        return {
            "model_version": MODEL_VERSION,
            "row_count": len(rows),
            "instruction": (
                "Leave Engineering Comments / Estimator Comments / Root Cause blank for "
                "manual completion during Estimation Team review."
            ),
            "rows": rows,
        }
