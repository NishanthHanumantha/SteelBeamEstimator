"""
Phase QA.1 — Engineering Accuracy Benchmark & Validation Framework
Package: PhaseQA.1_engineering_accuracy_validation
MODEL_VERSION: 6.5.1

This package provides a deterministic, read-only benchmarking framework to
objectively measure the accuracy of every pipeline stage against manually
verified engineering ground truth.

NO LLM. NO ENGINEERING DECISIONS. NO MODIFICATION OF EXISTING PIPELINE.
"""

from benchmark_models import (
    MODEL_VERSION,
    EngineeringBenchmarkResult,
    KPIRecord,
    BeamAccuracyRecord,
    GeometryErrorRecord,
    PatternComparisonRecord,
    BBSRowRecord,
    ErrorEntry,
    classify_score,
    safe_pct,
    DEFAULT_WEIGHTS,
    CLASSIFICATION_THRESHOLDS,
)
from ground_truth_loader import GroundTruth, GroundTruthLoader, GroundTruthLoadError
from benchmark_loader import ModelOutputLoader, BenchmarkLoadError
from phase_qa1_orchestrator import PhaseQA1Orchestrator, BenchmarkValidationError

__version__ = MODEL_VERSION
__all__ = [
    "MODEL_VERSION",
    "EngineeringBenchmarkResult",
    "KPIRecord",
    "BeamAccuracyRecord",
    "GeometryErrorRecord",
    "PatternComparisonRecord",
    "BBSRowRecord",
    "ErrorEntry",
    "classify_score",
    "safe_pct",
    "DEFAULT_WEIGHTS",
    "CLASSIFICATION_THRESHOLDS",
    "GroundTruth",
    "GroundTruthLoader",
    "GroundTruthLoadError",
    "ModelOutputLoader",
    "BenchmarkLoadError",
    "PhaseQA1Orchestrator",
    "BenchmarkValidationError",
]
