"""
Stirrup Recovery Models — Phase SI.0
Data classes for all SI.0 artefacts.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class RecoverySource(str, Enum):
    ANNOTATION   = "ANNOTATION"          # valid @-notation found in annotation_features
    SHARED_GROUP = "SHARED_GROUP"        # adopted from a beam in the same drawing group
    PROXIMITY    = "PROXIMITY"           # adopted from most span-similar beam with annotation
    INFERENCE    = "ENGINEERING_INFERENCE"   # derived from IS 456 engineering rules
    NO_STIRRUP   = "NO_STIRRUP"          # beam genuinely has no stirrup (open links/steel)
    BENCHMARK    = "BENCHMARK_RETAINED"  # existing valid stirrup — not changed


class RecoveryDecision(str, Enum):
    RETAINED  = "RETAINED"   # existing stirrup is valid → keep
    RECOVERED = "RECOVERED"  # invalid → successfully recovered
    FAILED    = "FAILED"     # invalid → no recovery possible


class InvalidReason(str, Enum):
    NO_AT_SIGN   = "NO_AT_SIGN"
    NO_SPACING   = "NO_SPACING_MM"
    LONGITUDINAL = "LONGITUDINAL_BAR_MISCLASSIFIED"
    EMPTY        = "EMPTY_STIRRUP_LIST"


@dataclass
class StirrupCandidate:
    """A valid stirrup annotation found anywhere in the feature database."""
    feature_id: str
    bar_id: str
    source_beam_id: str
    callout: str
    diameter_mm: float
    legs: int
    spacings_mm: List[int]
    spacing_mm: float
    has_hook: bool
    confidence: float
    annotation_layer: str = ""
    has_at_sign: bool = True


@dataclass
class BeamRecoveryResult:
    """Recovery outcome for a single beam."""
    beam_id: str
    span_mm: float
    depth_mm: Optional[float]
    width_mm: Optional[float]
    decision: RecoveryDecision
    source: RecoverySource
    invalid_reason: Optional[InvalidReason]
    original_label: Optional[str]
    recovered_label: Optional[str]
    recovered_diameter_mm: Optional[float]
    recovered_spacing_mm: Optional[float]
    recovered_spacings_mm: List[int] = field(default_factory=list)
    recovered_legs: int = 2
    recovery_confidence: float = 0.0
    engineering_evidence: str = ""
    traceability: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveredStirrupObject:
    """Replacement stirrup object that replaces the invalid L.2 entry."""
    bar_id: str
    source_bar_id: str
    beam_id: str
    semantic_role: str = "STIRRUP"
    diameter_mm: float = 8.0
    quantity: int = 2
    steel_grade: str = "Y"
    bar_label: str = ""
    position_zone: str = "TRANSVERSE_ZONE"
    extent: str = "FULL_SPAN"
    continuity: str = "SINGLE_BEAM"
    support_zone: None = None
    coverage_ratio: float = 1.0
    spacing_mm: Optional[float] = None
    classification_evidence: str = ""
    classification_confidence: str = "MEDIUM"
    source_pipeline_role: str = "STIRRUP"
    is_corrected: bool = True
    is_reference_anchored: bool = False
    recovered: bool = True
    recovery_source: str = ""
    recovery_confidence: float = 0.0
    recovery_engineering_note: str = ""
    recovery_traceability: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SI0EngineResult:
    """Aggregate result for the full SI.0 run."""
    model_version: str = "6.6.2"
    total_beams: int = 0
    beams_with_stirrups: int = 0
    invalid_stirrups_found: int = 0
    benchmark_retained: int = 0
    recovered_from_annotation: int = 0
    recovered_from_shared_group: int = 0
    recovered_from_proximity: int = 0
    recovered_from_inference: int = 0
    failed_recovery: int = 0
    beam_results: List[BeamRecoveryResult] = field(default_factory=list)
    validation_passed: bool = False
    validation_errors: List[str] = field(default_factory=list)
