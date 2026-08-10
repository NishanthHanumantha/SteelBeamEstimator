"""
P2.1 configuration — diagnostic / counterfactual only.
MODEL_VERSION: 10.5.3
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

MODEL_VERSION = "10.5.3"
PHASE_ID = "P2.1"

EXPECTED_LEADER_COUNT = 23
EXPECTED_ELIGIBLE_COUNT = 5


@dataclass(frozen=True)
class P21Config:
    set_key: str = "Fourth"
    drawing_set: str = "Fourth Set Drawings"
    expected_leader_count: int = EXPECTED_LEADER_COUNT
    expected_eligible_count: int = EXPECTED_ELIGIBLE_COUNT
    sort_keys: Tuple[str, ...] = ("beam_id", "entity_id", "stable_key")
    # Labels only — policies are diagnostic, not production rules
    counterfactual_label: str = "COUNTERFACTUAL — NOT PRODUCTION OWNERSHIP"


DEFAULT_CONFIG = P21Config()
