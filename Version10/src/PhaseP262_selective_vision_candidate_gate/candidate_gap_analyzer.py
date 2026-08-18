"""Annotation vs deterministic-object gap analysis. Production signals only."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .gate_decision import build_gate_decision
from .gate_features import extract_gate_features


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


__all__ = ["analyze_beam_gap", "extract_gate_features"]
