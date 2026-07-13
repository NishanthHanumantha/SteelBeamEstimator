"""
Pattern Models — canonical dataclasses for Phase L.3.

EngineeringPattern is the single output record per beam.
All sub-fields are plain dicts for JSON serialisability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

PHASE = "L.3"
MODEL_VERSION = "6.5.0"


def make_pattern_id(beam_id: str) -> str:
    return f"PAT::L3::{beam_id}"


# ── span pattern constants ────────────────────────────────────────────────────
class SpanPattern:
    SIMPLY_SUPPORTED = "SIMPLY_SUPPORTED"
    CONTINUOUS_END_SPAN = "CONTINUOUS_END_SPAN"
    CONTINUOUS_INTERIOR_SPAN = "CONTINUOUS_INTERIOR_SPAN"
    CANTILEVER = "CANTILEVER"
    TRANSFER_BEAM = "TRANSFER_BEAM"
    DEEP_BEAM = "DEEP_BEAM"
    UNKNOWN = "UNKNOWN"


# ── continuity pattern constants ──────────────────────────────────────────────
class ContinuityPattern:
    SINGLE_BEAM = "SINGLE_BEAM"
    MULTI_BEAM_CONTINUOUS = "MULTI_BEAM_CONTINUOUS"
    CONTINUOUS_CHAIN = "CONTINUOUS_CHAIN"
    DISCONTINUOUS = "DISCONTINUOUS"


# ── reinforcement pattern constants ───────────────────────────────────────────
class ReinforcementPattern:
    TOP_DOMINANT = "TOP_REINFORCEMENT_DOMINANT"
    BOTTOM_DOMINANT = "BOTTOM_REINFORCEMENT_DOMINANT"
    BALANCED = "BALANCED_REINFORCEMENT"
    TOP_HEAVY = "TOP_HEAVY"
    BOTTOM_HEAVY = "BOTTOM_HEAVY"
    SUPPORT_HEAVY = "SUPPORT_HEAVY"
    MIDSPAN_HEAVY = "MIDSPAN_HEAVY"
    EXTRA_TOP = "EXTRA_TOP_BARS"
    EXTRA_BOTTOM = "EXTRA_BOTTOM_BARS"
    MINIMAL = "MINIMAL_REINFORCEMENT"
    UNKNOWN = "UNKNOWN"


# ── support pattern constants ─────────────────────────────────────────────────
class SupportPattern:
    NONE = "NO_SUPPORT_REINFORCEMENT"
    ONE_SIDE = "ONE_SIDE_REINFORCEMENT"
    BOTH_SIDES = "BOTH_SIDE_REINFORCEMENT"
    INTERMEDIATE = "INTERMEDIATE_SUPPORT_REINFORCEMENT"
    CONGESTED = "SUPPORT_CONGESTION"
    LONG_ZONE = "LONG_SUPPORT_ZONE"
    SHORT_ZONE = "SHORT_SUPPORT_ZONE"
    UNKNOWN = "UNKNOWN"


# ── structural behaviour constants ────────────────────────────────────────────
class StructuralBehavior:
    SAGGING = "SAGGING_BEAM"
    HOGGING = "HOGGING_BEAM"
    HOGGING_BEAM = "HOGGING_BEAM"
    SAGGING_AND_HOGGING = "SAGGING_AND_HOGGING"
    SUPPORT_MOMENT_DOMINANT = "SUPPORT_MOMENT_DOMINANT"
    MIDSPAN_MOMENT_DOMINANT = "MIDSPAN_MOMENT_DOMINANT"
    SYMMETRIC = "SYMMETRIC"
    ASYMMETRIC = "ASYMMETRIC"
    UNKNOWN = "UNKNOWN"


# ── intensity labels ──────────────────────────────────────────────────────────
class Intensity:
    HEAVY = "HEAVY"
    MODERATE = "MODERATE"
    LIGHT = "LIGHT"
    NONE = "NONE"


# ── confidence levels ─────────────────────────────────────────────────────────
class ConfidenceLevel:
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ── main dataclass ────────────────────────────────────────────────────────────

@dataclass
class EngineeringPattern:
    pattern_id: str
    beam_id: str
    beam_name: str
    pattern_version: str

    # Pattern fields
    span_pattern: str                     # SpanPattern constant
    support_pattern: str                  # SupportPattern constant
    reinforcement_pattern: str            # ReinforcementPattern constant
    continuity_pattern: str               # ContinuityPattern constant
    structural_behavior: str              # StructuralBehavior constant

    support_reinforcement_pattern: str    # Intensity constant
    midspan_reinforcement_pattern: str    # Intensity constant
    top_bottom_balance: str              # e.g. "TOP_HEAVY", "BOTTOM_HEAVY", "BALANCED"
    extra_bar_pattern: str               # e.g. "EXTRA_TOP", "EXTRA_BOTTOM", "NO_EXTRA"
    anchorage_pattern: str               # e.g. "STANDARD", "HOOK_ANCHORAGE", "UNKNOWN"
    development_length_pattern: str      # e.g. "STANDARD", "EXTENDED", "UNKNOWN"
    lap_pattern: str                     # e.g. "NO_LAP", "LAP_AT_SUPPORT", "UNKNOWN"

    dominant_reinforcement: str          # e.g. "TOP_MAIN_BARS", "BOTTOM_MAIN_BARS"
    classification_confidence: float     # 0–1
    confidence_level: str                # HIGH / MEDIUM / LOW

    engineering_notes: List[str] = field(default_factory=list)
    traceability: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "beam_id": self.beam_id,
            "beam_name": self.beam_name,
            "pattern_version": self.pattern_version,
            "span_pattern": self.span_pattern,
            "support_pattern": self.support_pattern,
            "reinforcement_pattern": self.reinforcement_pattern,
            "continuity_pattern": self.continuity_pattern,
            "structural_behavior": self.structural_behavior,
            "support_reinforcement_pattern": self.support_reinforcement_pattern,
            "midspan_reinforcement_pattern": self.midspan_reinforcement_pattern,
            "top_bottom_balance": self.top_bottom_balance,
            "extra_bar_pattern": self.extra_bar_pattern,
            "anchorage_pattern": self.anchorage_pattern,
            "development_length_pattern": self.development_length_pattern,
            "lap_pattern": self.lap_pattern,
            "dominant_reinforcement": self.dominant_reinforcement,
            "classification_confidence": self.classification_confidence,
            "confidence_level": self.confidence_level,
            "engineering_notes": self.engineering_notes,
            "traceability": self.traceability,
        }
