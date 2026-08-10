"""
P2.3.1 configuration — Controlled Engineering Recompute / Steel Re-benchmark.
MODEL_VERSION: 10.5.6
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


MODEL_VERSION = "10.5.6"
PHASE_ID = "P2.3.1"
PRODUCTION_POLICY = "E_STRONG_COMBINED"
REFERENCE_POSITIVE_KEY = "B16::LDR::7A1FFD68"
EXPECTED_MIGRATED_ENTITIES = (
    "LDR::7A1FFD68",
    "ARR::4C3D2D29",
    "LTGT::LDR::7A1FFD68",
)
EXPECTED_BASELINE_NODES = 288
EXPECTED_BASELINE_LEADERS = 25
EXPECTED_CONTROLLED_NODES = 291
EXPECTED_CONTROLLED_LEADERS = 26


class DecisionClass(str, Enum):
    IMPROVEMENT = "ENGINEERING IMPROVEMENT CONFIRMED"
    NEUTRAL = "ENGINEERING IMPACT NEUTRAL"
    NEGATIVE = "ENGINEERING IMPACT NEGATIVE"
    FAILED = "CONTROLLED RECOMPUTE FAILED"


@dataclass(frozen=True)
class P231Config:
    set_key: str = "Fourth"
    drawing_set: str = "Fourth Set Drawings"
    leader_chain_recovery_policy: str = PRODUCTION_POLICY
    mutate_historical_t18: bool = False
    mutate_historical_excel: bool = False
    label: str = "CONTROLLED ENGINEERING RECOMPUTE — MEASUREMENT ONLY"


DEFAULT_CONFIG = P231Config()
