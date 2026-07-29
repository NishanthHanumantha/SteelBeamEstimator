"""
pipeline_execution_models.py — Data models for V.RUN.1 pipeline re-execution.
MODEL_VERSION: 7.2.0
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class StageDefinition:
    """Defines one pipeline stage and how to run it."""
    stage_id:       str
    name:           str
    runner_script:  str        # relative path under Version8/
    cli_args:       List[str]  # extra CLI arguments (e.g. benchmark folder)
    output_dir:     str        # relative path to primary output directory
    expected_files: List[str]  # key artefact filenames expected
    timeout_s:      int = 300  # max seconds to wait


@dataclass
class StageResult:
    """Result of executing one pipeline stage."""
    stage_id:         str
    name:             str
    status:           str          # SUCCESS / FAILED / TIMEOUT / SKIPPED
    exit_code:        int
    start_time:       str
    end_time:         str
    duration_s:       float
    stdout_tail:      str
    stderr_tail:      str
    output_files:     List[str]
    input_beam_count: int
    output_beam_count: int
    beam_ids:         List[str]
    lost_beams:       List[str]
    notes:            str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class StaleArchiveRecord:
    """Records what was archived before the fresh run."""
    stage_id:      str
    source_path:   str
    archive_path:  str
    file_count:    int
    archived_at:   str


@dataclass
class PipelineExecutionResult:
    """Full result of the V.RUN.1 pipeline run."""
    phase_id:        str
    model_version:   str
    started_at:      str
    completed_at:    str
    total_duration_s: float
    stages:          List[StageResult]
    beam_propagation: List[dict]
    stale_archives:  List[StaleArchiveRecord]
    validation:      List[dict]
    overall_status:  str    # SUCCESS / PARTIAL / FAILED
    workbook_path:   Optional[str]

    def to_dict(self) -> dict:
        return {
            "phase_id":        self.phase_id,
            "model_version":   self.model_version,
            "started_at":      self.started_at,
            "completed_at":    self.completed_at,
            "total_duration_s": self.total_duration_s,
            "stages":          [s.to_dict() for s in self.stages],
            "beam_propagation": self.beam_propagation,
            "stale_archives":  [a.__dict__ for a in self.stale_archives],
            "validation":      self.validation,
            "overall_status":  self.overall_status,
            "workbook_path":   self.workbook_path,
        }
