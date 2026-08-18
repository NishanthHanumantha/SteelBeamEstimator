"""Replay frozen P2.6.1 Vision under observed P2.6.4 decisions (unchanged routing)."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from PhaseP264_selective_role_gap_gate.replay_runner import (
    apply_gate_to_frozen as _apply,
)


def apply_gate_to_frozen(
    *,
    decisions: List[Dict[str, Any]],
    frozen_candidates: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    return _apply(decisions=decisions, frozen_candidates=frozen_candidates)


__all__ = ["apply_gate_to_frozen"]
