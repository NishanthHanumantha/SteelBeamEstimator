"""
QA.4.2 configuration — evidence-driven, no arbitrary envelope expansion.
MODEL_VERSION: 10.5.1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Tuple

MODEL_VERSION = "10.5.1"
PHASE_ID = "QA.4.2"

# Reuse QA.4.1 / T18 diagnostic band constants (not new production thresholds)
from PhaseQA41_dropped_entity_recovery_audit.geometry_helpers import (  # noqa: E402
    ANN_REACH_DEPTH_FACTOR,
    SUPPORT_EXT_MM,
)


@dataclass(frozen=True)
class CandidateRecoveryConfig:
    """Configuration for append-only candidate recovery."""

    recovery_enabled: bool = True
    drawing_set_in_scope: str = "Fourth Set Drawings"
    set_key: str = "Fourth"
    target_audit_category: str = "ENVELOPE_NEVER_CANDIDATE"
    allowed_recovery_potentials: Tuple[str, ...] = ("HIGH",)
    # Spatial classes allowed for HIGH recovery eligibility (from QA.4.1 evidence)
    allowed_spatial_relationships: Tuple[str, ...] = ("BOUNDARY", "NEAR_OUTSIDE")
    # Entity types that map to T18 satellite / beam nodes (existing engine paths)
    recoverable_entity_types: FrozenSet[str] = field(
        default_factory=lambda: frozenset({"LeaderArrow", "LeaderTarget", "Beam"})
    )
    # Beam mark nodes are always accepted by T18 but are not reinforcement candidates
    exclude_entity_types_from_new_recovery: FrozenSet[str] = field(
        default_factory=lambda: frozenset({"Beam"})
    )
    require_target_beam_context: bool = True
    require_longitudinal_overlap: bool = True
    reject_neighbour_ambiguity: bool = True
    reject_inside_other_beam_envelope: bool = True
    # Diagnostic evaluation of MEDIUM/LOW (no candidate emission unless HIGH)
    diagnostically_evaluate_medium_low: bool = True
    # Existing T18 constants exposed for traceability only
    support_ext_mm: float = SUPPORT_EXT_MM
    ann_reach_depth_factor: float = ANN_REACH_DEPTH_FACTOR
    # Expected baseline gates (derived from QA.4.1; validated, not hard-coded as population)
    expected_original_dropped: int = 104
    expected_envelope_population: int = 77
    expected_high_envelope_population: int = 51
    # Deterministic sort keys
    sort_keys: Tuple[str, ...] = ("beam_id", "entity_id", "stable_key")


DEFAULT_CONFIG = CandidateRecoveryConfig()
