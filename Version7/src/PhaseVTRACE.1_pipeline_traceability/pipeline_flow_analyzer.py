"""
pipeline_flow_analyzer.py — Generates the pipeline flow diagram (text + data)
and identifies the first failure stage.
MODEL_VERSION: 7.1.2  |  READ-ONLY
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from .engineering_trace_models import StageComparison, StageSnapshot


class PipelineFlowAnalyzer:
    """
    Produces a human-readable flow report and identifies the first stage
    where beam count decreases.
    """

    def __init__(self, stage_order: List[str]):
        self._stage_order = stage_order

    def build_flow(
        self,
        snapshots: Dict[str, StageSnapshot],
        comparisons: List[StageComparison],
    ) -> dict:
        """Return flow report with stage-by-stage counts."""
        rows     = []
        first_failure: Optional[str]  = None
        first_failure_delta: int      = 0

        for stage_id in self._stage_order:
            snap = snapshots.get(stage_id)
            if snap is None:
                continue
            rows.append({
                "stage_id":        stage_id,
                "stage_name":      snap.stage_name,
                "beam_count":      snap.beam_count,
                "artefact_exists": snap.artefact_exists,
            })

        # Identify first failure (where count strictly decreases from VROOT1)
        source_count = snapshots.get("VROOT1", StageSnapshot(
            stage_id="", stage_name="", beam_count=0, beam_ids=[],
            beam_uuids={}, input_files=[], output_file="",
            artefact_exists=False, timestamp=None, raw_metadata={})).beam_count

        prev_stage_id  = "VROOT1"
        for comp in comparisons:
            if comp.delta < 0 and first_failure is None:
                first_failure       = comp.to_stage
                first_failure_delta = comp.delta
            prev_stage_id = comp.to_stage

        # Build ASCII flow diagram
        lines = ["Pipeline Flow Diagram", "=" * 40]
        for row in rows:
            mark = ""
            if first_failure and row["stage_id"] == first_failure:
                mark = "  *** FIRST FAILURE ***"
            cnt_str = str(row["beam_count"]) if row["artefact_exists"] else "N/A"
            lines.append(f"  {row['stage_id']:<14} {cnt_str:>6} beams{mark}")
            lines.append("  ↓")
        lines.append("  [END]")

        return {
            "flow_rows":           rows,
            "first_failure_stage": first_failure,
            "first_failure_delta": first_failure_delta,
            "source_beam_count":   source_count,
            "flow_diagram":        "\n".join(lines),
            "comparisons":         [c.to_dict() for c in comparisons],
        }
