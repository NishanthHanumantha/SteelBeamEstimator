"""
benchmark3_models.py — Data models for Phase V.TEST.3.
MODEL_VERSION: 8.1.1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BenchmarkFile:
    filename: str
    relative_path: str
    file_type: str
    size_bytes: int
    copied_to: str


@dataclass
class Benchmark3Manifest:
    benchmark_id: str
    timestamp: str
    source_folder: str
    destination_folder: str
    model_version: str
    project_name: str = ""
    building: str = ""
    floor: str = ""
    files: List[BenchmarkFile] = field(default_factory=list)
    total_files: int = 0
    dxf_count: int = 0
    drawing_classification: Dict[str, int] = field(default_factory=dict)
    validation_passed: bool = False
    issues: List[str] = field(default_factory=list)


@dataclass
class PipelineStageResult:
    stage_id: str
    stage_name: str
    script_path: str
    success: bool
    exit_code: int
    elapsed_seconds: float
    output_files: List[str] = field(default_factory=list)
    error_message: str = ""
    stderr_tail: str = ""


@dataclass
class PipelineRunResult:
    stages: List[PipelineStageResult] = field(default_factory=list)
    total_elapsed_seconds: float = 0.0
    stages_executed: int = 0
    stages_passed: int = 0
    stages_failed: int = 0
    success_rate_pct: float = 0.0
    pipeline_completed: bool = False


@dataclass
class ReadinessScore:
    dimension: str
    score: float
    max_score: float = 100.0
    detail: str = ""


@dataclass
class FullBenchmark3Result:
    model_version: str
    benchmark_id: str
    timestamp: str
    manifest: Optional[Benchmark3Manifest] = None
    pipeline: Optional[PipelineRunResult] = None
    discovery_summary: Dict[str, Any] = field(default_factory=dict)
    beam_summary: Dict[str, Any] = field(default_factory=dict)
    general_notes_summary: Dict[str, Any] = field(default_factory=dict)
    reinforcement_summary: Dict[str, Any] = field(default_factory=dict)
    interpretation_summary: Dict[str, Any] = field(default_factory=dict)
    engineering_bar_summary: Dict[str, Any] = field(default_factory=dict)
    production_summary: Dict[str, Any] = field(default_factory=dict)
    generalization_audit: Dict[str, Any] = field(default_factory=dict)
    readiness_scores: List[ReadinessScore] = field(default_factory=list)
    overall_readiness_score: float = 0.0
    readiness_classification: str = "NOT READY"
    warnings: List[str] = field(default_factory=list)
    validation_rules: Dict[str, bool] = field(default_factory=dict)
    overall_passed: bool = False
    recommended_next_phase: str = "R.4 — Engineering Intent Resolution Engine"
