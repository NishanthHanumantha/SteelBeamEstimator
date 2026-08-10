"""
P2.3 configuration — Controlled Production Gate + Re-benchmark.
MODEL_VERSION: 10.5.5
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


MODEL_VERSION = "10.5.5"
PHASE_ID = "P2.3"

EXPECTED_LEADER_COUNT = 23
PRODUCTION_POLICY = "E_STRONG_COMBINED"
REFERENCE_POSITIVE_KEY = "B16::LDR::7A1FFD68"

# Graph relationship types that may propagate from a recovered leader
# into effective ownership (existing architecture only — no new association rules).
PROPAGATION_EDGE_TYPES = (
    "HAS_ARROW",
    "TARGETS",
)


class GateMode(str, Enum):
    OFF = "OFF"  # baseline — exact T18
    BASELINE = "BASELINE"  # alias of OFF
    CONTROLLED = "CONTROLLED"  # E_STRONG_COMBINED overlay


class DecisionClass(str, Enum):
    PASS_CONTROLLED_IMPROVEMENT = "PASS - CONTROLLED IMPROVEMENT"
    PASS_SAFE_NO_MATERIAL = "PASS - SAFE BUT NO MATERIAL IMPROVEMENT"
    PASS_DIAGNOSTIC_UNCLEAR = "PASS - DIAGNOSTIC SUCCESS / ENGINEERING IMPACT UNCLEAR"
    FAIL_REGRESSION = "FAIL - REGRESSION"
    FAIL_CONTAMINATION = "FAIL - CONTAMINATION"
    FAIL_UNEXPLAINED = "FAIL - UNEXPLAINED OWNERSHIP MIGRATION"
    FAIL_NONDETERMINISTIC = "FAIL - NON-DETERMINISTIC"


@dataclass(frozen=True)
class P23Config:
    set_key: str = "Fourth"
    drawing_set: str = "Fourth Set Drawings"
    leader_chain_recovery_policy: str = PRODUCTION_POLICY
    leader_chain_recovery_enabled: bool = True
    # Never mutate historical web_run T18 artefacts; write overlay under P2.3 only.
    mutate_historical_t18: bool = False
    expected_leader_count: int = EXPECTED_LEADER_COUNT
    sort_keys: Tuple[str, ...] = ("beam_id", "leader_id", "stable_key")
    label: str = "CONTROLLED PRODUCTION EXPERIMENT — E_STRONG_COMBINED OVERLAY"


DEFAULT_CONFIG = P23Config()
