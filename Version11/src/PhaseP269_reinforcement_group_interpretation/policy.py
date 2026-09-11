"""P2.6.9 policy. Runtime extraction stays GT-free and does not change routing."""
from __future__ import annotations

from PhaseP264_selective_role_gap_gate.policy import (
    FORBIDDEN_GATE_REASONS,
    FORBIDDEN_GATE_TOKENS,
    assert_no_forbidden_reason,
)

from .config import ENGINEERING_CHANGES, PRODUCTION_WRITE, SHADOW_ONLY

__all__ = [
    "ENGINEERING_CHANGES",
    "FORBIDDEN_GATE_REASONS",
    "FORBIDDEN_GATE_TOKENS",
    "PRODUCTION_WRITE",
    "SHADOW_ONLY",
    "assert_no_forbidden_reason",
]
