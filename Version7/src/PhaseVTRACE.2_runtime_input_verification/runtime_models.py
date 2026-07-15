"""
runtime_models.py — Data models for V.TRACE.2 runtime diagnostics.
MODEL_VERSION: 7.1.3  |  READ-ONLY
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class RuntimeFile:
    """A single file loaded (or expected to be loaded) by L.2."""
    key:             str              # InterpretationCollector key
    absolute_path:   str
    relative_path:   str
    exists:          bool
    size_bytes:      int
    mtime_epoch:     Optional[float]
    mtime_iso:       Optional[str]
    sha256:          Optional[str]
    version:         Optional[str]   # Version5 / Version6 / Version7
    benchmark_id:    Optional[str]   # Benchmark_Set_1 / Benchmark_Set_2 / UNKNOWN
    model_version:   Optional[str]
    beam_count:      Optional[int]
    beam_ids:        List[str]
    phase_origin:    Optional[str]
    load_status:     str             # LOADED / MISSING / EMPTY

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class RuntimeLoadEvent:
    """A single file-load event captured during L.2 runtime simulation."""
    sequence:        int
    key:             str
    absolute_path:   str
    beam_count:      Optional[int]
    beam_ids:        List[str]
    load_status:     str
    caller:          str
    note:            str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class RuntimeInputSnapshot:
    """Complete input state visible to L.2 at the moment of execution."""
    project_root:          str
    v5_adapter_root:       str
    files:                 Dict[str, RuntimeFile]    # key → RuntimeFile
    adapter_beam_count:    int
    adapter_beam_ids:      List[str]
    discover_beams_result: List[str]      # what _discover_beams() actually returns
    discover_beams_source: str            # "beam_schedule" / "reinforcement_objects" / "fallback"
    l2_output_beam_count:  int
    l2_output_timestamp:   Optional[str]
    adapter_timestamp:     Optional[str]
    output_is_stale:       bool

    def to_dict(self) -> dict:
        return {
            "project_root":          self.project_root,
            "v5_adapter_root":       self.v5_adapter_root,
            "files":                 {k: v.to_dict() for k, v in self.files.items()},
            "adapter_beam_count":    self.adapter_beam_count,
            "adapter_beam_ids":      self.adapter_beam_ids,
            "discover_beams_result": self.discover_beams_result,
            "discover_beams_source": self.discover_beams_source,
            "l2_output_beam_count":  self.l2_output_beam_count,
            "l2_output_timestamp":   self.l2_output_timestamp,
            "adapter_timestamp":     self.adapter_timestamp,
            "output_is_stale":       self.output_is_stale,
        }


@dataclass
class PipelineInputReport:
    """Full 12-section V.TRACE.2 report."""
    phase:          str
    model_version:  str
    generated_at:   str
    snapshot:       RuntimeInputSnapshot
    root_cause:     str
    recommendation: str
    validation:     List[dict]

    def to_dict(self) -> dict:
        return {
            "phase":          self.phase,
            "model_version":  self.model_version,
            "generated_at":   self.generated_at,
            "snapshot":       self.snapshot.to_dict(),
            "root_cause":     self.root_cause,
            "recommendation": self.recommendation,
            "validation":     self.validation,
        }
