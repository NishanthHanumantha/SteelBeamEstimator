"""Counterfactual replay of frozen P2.6.1 Vision responses under the P2.6.4 gate."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from PhaseP263_longitudinal_aware_gate.replay_runner import (
    apply_gate_to_frozen as _apply,
)


def apply_gate_to_frozen(
    *,
    decisions: List[Dict[str, Any]],
    frozen_candidates: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    return _apply(decisions=decisions, frozen_candidates=frozen_candidates)


__all__ = ["apply_gate_to_frozen"]
