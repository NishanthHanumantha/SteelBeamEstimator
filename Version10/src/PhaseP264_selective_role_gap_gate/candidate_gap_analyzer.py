"""Thin wrap around P2.6.4 coverage + role-gap + gate decision."""
from __future__ import annotations

from typing import Any, Dict, Optional

from PhaseP263_longitudinal_aware_gate.longitudinal_coverage import (
    evaluate_longitudinal_coverage,
)

from .gate_decision import build_gate_decision
from .role_gap import evaluate_selective_role_gap


def analyze_beam_gap(
    *,
    beam_id: str,
    region_id: str,
    rec: Dict[str, Any],
    model: Optional[Dict[str, Any]],
    **kwargs: Any,
) -> Dict[str, Any]:
    return build_gate_decision(
        beam_id=beam_id,
        region_id=region_id,
        rec=rec,
        model=model,
        **kwargs,
    )


__all__ = [
    "analyze_beam_gap",
    "evaluate_longitudinal_coverage",
    "evaluate_selective_role_gap",
]
