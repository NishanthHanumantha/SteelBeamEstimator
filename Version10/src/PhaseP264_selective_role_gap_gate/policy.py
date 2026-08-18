"""P2.6.4 policy. Runtime gate stays GT-free, stratum-free, and stirrup-frozen."""
from __future__ import annotations

from PhaseP263_longitudinal_aware_gate.policy import (
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
