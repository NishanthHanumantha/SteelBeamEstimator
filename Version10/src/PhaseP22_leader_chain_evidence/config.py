"""
P2.2 configuration — Leader-Chain Evidence Enhancement.
MODEL_VERSION: 10.5.4

DIAGNOSTIC / PRODUCTION-CANDIDATE ONLY until an explicit production gate
is enabled in a later phase.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


MODEL_VERSION = "10.5.4"
PHASE_ID = "P2.2"

EXPECTED_LEADER_COUNT = 23
EXPECTED_ELIGIBLE_COUNT = 5
EXPECTED_POLICY_E_ACCEPT_ALL = 1
EXPECTED_POLICY_E_ACCEPT_ELIGIBLE = 1

# Reference fixture identity (validation only — NOT a hard-coded exception path)
REFERENCE_POSITIVE_KEY = "B16::LDR::7A1FFD68"

# Known contamination / do-not-recover keys (validation only)
KNOWN_NEGATIVE_KEYS = (
    "B16::LDR::49842AC8",
    "B16::LDR::50092321",
    "B18::LDR::1EDDB869",
    "B19::LDR::027AB042",
    "B19::LDR::056CE421",
    "B29::LDR::58F9C249",
    "B46::LDR::FE5B8017",
)

PRODUCTION_POLICY = "E_STRONG_COMBINED"


class ProductionGate(str, Enum):
    """Explicit production safety gate states."""

    DIAGNOSTIC_ONLY = "DIAGNOSTIC_ONLY"
    PRODUCTION_CANDIDATE = "PRODUCTION_CANDIDATE"
    PRODUCTION_ENABLED = "PRODUCTION_ENABLED"


class EnhancedDecision(str, Enum):
    ACCEPT_CANDIDATE = "ACCEPT_CANDIDATE"
    REJECT = "REJECT"
    CURRENT_T18 = "CURRENT_T18"


@dataclass(frozen=True)
class P22Config:
    set_key: str = "Fourth"
    drawing_set: str = "Fourth Set Drawings"
    expected_leader_count: int = EXPECTED_LEADER_COUNT
    expected_eligible_count: int = EXPECTED_ELIGIBLE_COUNT
    expected_policy_e_accept_all: int = EXPECTED_POLICY_E_ACCEPT_ALL
    expected_policy_e_accept_eligible: int = EXPECTED_POLICY_E_ACCEPT_ELIGIBLE
    sort_keys: Tuple[str, ...] = ("beam_id", "entity_id", "stable_key")
    # P2.2 must start diagnostic-only; BeamOwnership is never written in this mode.
    production_gate: ProductionGate = ProductionGate.DIAGNOSTIC_ONLY
    production_policy: str = PRODUCTION_POLICY
    write_beam_ownership: bool = False
    label: str = "DIAGNOSTIC / PRODUCTION-CANDIDATE ONLY"


DEFAULT_CONFIG = P22Config()
