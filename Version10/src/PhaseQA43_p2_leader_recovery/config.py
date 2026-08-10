"""
QA.4.3 configuration — P2 Leader Recovery (append-only).
MODEL_VERSION: 10.5.2
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from PhaseQA41_dropped_entity_recovery_audit.geometry_helpers import (
    ANN_REACH_DEPTH_FACTOR,
    SUPPORT_EXT_MM,
)

MODEL_VERSION = "10.5.2"
PHASE_ID = "QA.4.3"


@dataclass(frozen=True)
class LeaderRecoveryConfig:
    recovery_enabled: bool = True
    drawing_set_in_scope: str = "Fourth Set Drawings"
    set_key: str = "Fourth"
    target_audit_category: str = "LEADER_CHAIN_FAILURE"
    # Potentials that may emit recovery candidate audit records for T18 confirmation
    candidate_emission_potentials: Tuple[str, ...] = ("HIGH", "MEDIUM")
    # Spatial classes that may be eligible (reuse QA.4.1 bands)
    allowed_spatial_for_emission: Tuple[str, ...] = (
        "BOUNDARY",
        "NEAR_OUTSIDE",
        "MODERATE_OUTSIDE",
    )
    reject_neighbour_ambiguity: bool = True
    reject_inside_other_beam_envelope: bool = True
    reject_far_outside: bool = True
    support_ext_mm: float = SUPPORT_EXT_MM
    ann_reach_depth_factor: float = ANN_REACH_DEPTH_FACTOR
    expected_original_dropped: int = 104
    expected_leader_population: int = 23
    sort_keys: Tuple[str, ...] = ("beam_id", "entity_id", "stable_key")


DEFAULT_CONFIG = LeaderRecoveryConfig()
