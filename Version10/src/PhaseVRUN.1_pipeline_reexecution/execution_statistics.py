"""
execution_statistics.py — Aggregates V.RUN.1 execution statistics.
MODEL_VERSION: 7.2.0
"""

from __future__ import annotations
import pathlib
from typing import List
from .pipeline_execution_models import StageResult

WORKSPACE = pathlib.Path(r"C:\Users\nishanth.h\SteelBeamEstimator")
V7        = WORKSPACE / "Version8"


class ExecutionStatistics:

    def compute(
        self,
        stages:       List[StageResult],
        propagation:  List[dict],
        freshness:    dict,
    ) -> dict:
        total_duration = sum(s.duration_s for s in stages)
        success_stages = [s for s in stages if s.status == "SUCCESS"]
        failed_stages  = [s for s in stages if s.status != "SUCCESS"]

        artefact_counts = {}
        for s in stages:
            artefact_counts[s.stage_id] = len(s.output_files)

        # Final beam count = last stage in propagation that has beams
        final_beam_count = 0
        for row in reversed(propagation):
            if row.get("beam_count", 0) > 0:
                final_beam_count = row["beam_count"]
                break

        # Total JSON files generated
        total_json = sum(
            1 for s in stages
            for f in s.output_files
            if f.endswith(".json")
        )

        # Workbook
        vb1_files = [s.output_files for s in stages if s.stage_id == "VB1"]
        workbook_files = []
        for flist in vb1_files:
            workbook_files += [f for f in flist if f.endswith(".xlsx")]

        return {
            "total_stages":       len(stages),
            "successful_stages":  len(success_stages),
            "failed_stages":      len(failed_stages),
            "total_duration_s":   round(total_duration, 2),
            "per_stage_duration": {s.stage_id: s.duration_s for s in stages},
            "artefact_counts":    artefact_counts,
            "total_json_files":   total_json,
            "initial_beam_count": propagation[0]["beam_count"] if propagation else 0,
            "final_beam_count":   final_beam_count,
            "total_artefacts_freshness_checked": freshness.get("total_artefacts_checked", 0),
            "stale_artefacts_remaining":         freshness.get("stale_artefacts", 0),
            "workbook_files":     workbook_files,
        }
