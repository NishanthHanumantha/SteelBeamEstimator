"""P2.6.7 policy. Live shadow benchmark stays GT-free and does not change routing."""
from __future__ import annotations

from PhaseP264_selective_role_gap_gate.policy import (
    FORBIDDEN_GATE_REASONS,
    FORBIDDEN_GATE_TOKENS,
    assert_no_forbidden_reason,
)

from .config import ENGINEERING_CHANGES, PRODUCTION_WRITE

__all__ = [
    "ENGINEERING_CHANGES",
    "FORBIDDEN_GATE_REASONS",
    "FORBIDDEN_GATE_TOKENS",
    "PRODUCTION_WRITE",
    "assert_no_forbidden_reason",
]
