"""
engineering_trace_models.py — Data models for V.TRACE.1 traceability framework.
MODEL_VERSION: 7.1.2  |  READ-ONLY
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class BeamStatus(str, Enum):
    PRESENT   = "PRESENT"
    MISSING   = "MISSING"
    ADDED     = "ADDED"
    MODIFIED  = "MODIFIED"
    DUPLICATE = "DUPLICATE"


class LossCategory(str, Enum):
    NOT_CREATED    = "NOT_CREATED"
    FILTERED       = "FILTERED"
    EMPTY_OBJECT   = "EMPTY_OBJECT"
    PIPELINE_SKIP  = "PIPELINE_SKIP"
    STALE_OUTPUT   = "STALE_OUTPUT"
    VALIDATION_DROP = "VALIDATION_DROP"
    UNKNOWN        = "UNKNOWN"


@dataclass
class StageSnapshot:
    """Beam state captured immediately after a pipeline stage."""
    stage_id:        str
    stage_name:      str
    beam_count:      int
    beam_ids:        List[str]
    beam_uuids:      Dict[str, str]       # beam_id → uuid
    input_files:     List[str]
    output_file:     str
    artefact_exists: bool
    timestamp:       Optional[str]
    raw_metadata:    Dict                  # raw fields from the artefact
    notes:           List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "stage_id":        self.stage_id,
            "stage_name":      self.stage_name,
            "beam_count":      self.beam_count,
            "beam_ids":        sorted(self.beam_ids),
            "beam_uuids":      self.beam_uuids,
            "input_files":     self.input_files,
            "output_file":     self.output_file,
            "artefact_exists": self.artefact_exists,
            "timestamp":       self.timestamp,
            "notes":           self.notes,
            "raw_metadata":    self.raw_metadata,
        }


@dataclass
class BeamLifecycleEntry:
    """A single stage record in a beam's lifecycle."""
    stage_id:   str
    status:     BeamStatus
    beam_uuid:  Optional[str]
    section:    Optional[str]
    note:       str = ""

    def to_dict(self) -> dict:
        return {
            "stage_id":  self.stage_id,
            "status":    self.status.value,
            "beam_uuid": self.beam_uuid,
            "section":   self.section,
            "note":      self.note,
        }


@dataclass
class BeamLifecycle:
    """Complete lifecycle of a single beam across all pipeline stages."""
    beam_id:       str
    stages:        Dict[str, BeamLifecycleEntry]   # stage_id → entry
    first_seen:    Optional[str]
    last_seen:     Optional[str]
    lost_at:       Optional[str]
    loss_category: Optional[LossCategory]
    loss_reason:   Optional[str]

    def to_dict(self) -> dict:
        return {
            "beam_id":       self.beam_id,
            "stages":        {k: v.to_dict() for k, v in self.stages.items()},
            "first_seen":    self.first_seen,
            "last_seen":     self.last_seen,
            "lost_at":       self.lost_at,
            "loss_category": self.loss_category.value if self.loss_category else None,
            "loss_reason":   self.loss_reason,
        }


@dataclass
class StageComparison:
    """Diff between two consecutive stages."""
    from_stage:       str
    to_stage:         str
    from_count:       int
    to_count:         int
    delta:            int
    beams_removed:    List[str]
    beams_added:      List[str]
    beams_retained:   List[str]
    retention_pct:    float
    loss_pct:         float

    def to_dict(self) -> dict:
        return {
            "from_stage":     self.from_stage,
            "to_stage":       self.to_stage,
            "from_count":     self.from_count,
            "to_count":       self.to_count,
            "delta":          self.delta,
            "beams_removed":  sorted(self.beams_removed),
            "beams_added":    sorted(self.beams_added),
            "beams_retained": sorted(self.beams_retained),
            "retention_pct":  round(self.retention_pct, 2),
            "loss_pct":       round(self.loss_pct, 2),
        }


@dataclass
class LostBeam:
    """A beam that disappeared from the pipeline."""
    beam_id:          str
    last_valid_stage: str
    first_lost_stage: str
    loss_category:    LossCategory
    loss_reason:      str
    confidence:       str            # HIGH / MEDIUM / LOW

    def to_dict(self) -> dict:
        return {
            "beam_id":          self.beam_id,
            "last_valid_stage": self.last_valid_stage,
            "first_lost_stage": self.first_lost_stage,
            "loss_category":    self.loss_category.value,
            "loss_reason":      self.loss_reason,
            "confidence":       self.confidence,
        }


@dataclass
class DuplicateRecord:
    """A duplicated beam ID or UUID detected within a stage."""
    stage_id:   str
    field:      str          # "beam_id", "beam_uuid", etc.
    value:      str
    count:      int
    note:       str = ""

    def to_dict(self) -> dict:
        return {
            "stage_id": self.stage_id,
            "field":    self.field,
            "value":    self.value,
            "count":    self.count,
            "note":     self.note,
        }


@dataclass
class RootCause:
    """Root cause assignment for beam loss at a specific stage."""
    stage_id:         str
    module_name:      str
    input_beam_count: int
    output_beam_count: int
    failure_category: LossCategory
    reason:           str
    confidence:       str
    affected_beams:   List[str]
    recommendation:   str

    def to_dict(self) -> dict:
        return {
            "stage_id":           self.stage_id,
            "module_name":        self.module_name,
            "input_beam_count":   self.input_beam_count,
            "output_beam_count":  self.output_beam_count,
            "delta":              self.input_beam_count - self.output_beam_count,
            "failure_category":   self.failure_category.value,
            "reason":             self.reason,
            "confidence":         self.confidence,
            "affected_beams":     sorted(self.affected_beams),
            "recommendation":     self.recommendation,
        }


@dataclass
class TraceStatistics:
    """Aggregated statistics for the entire pipeline trace."""
    total_beams_at_source:    int
    stage_counts:             Dict[str, int]
    first_failure_stage:      Optional[str]
    first_failure_delta:      int
    total_lost_beams:         int
    total_duplicate_records:  int
    pipeline_retention_pct:   float
    stages_with_loss:         List[str]
    stages_with_gain:         List[str]
    pipeline_complete:        bool

    def to_dict(self) -> dict:
        return {
            "total_beams_at_source":   self.total_beams_at_source,
            "stage_counts":            self.stage_counts,
            "first_failure_stage":     self.first_failure_stage,
            "first_failure_delta":     self.first_failure_delta,
            "total_lost_beams":        self.total_lost_beams,
            "total_duplicate_records": self.total_duplicate_records,
            "pipeline_retention_pct":  round(self.pipeline_retention_pct, 2),
            "stages_with_loss":        self.stages_with_loss,
            "stages_with_gain":        self.stages_with_gain,
            "pipeline_complete":       self.pipeline_complete,
        }
