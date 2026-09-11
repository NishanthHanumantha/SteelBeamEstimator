"""
Phase W.8 — Promote P2.6.10 evidence selection into production Hybrid.

Vision decides what reinforcement exists. Deterministic engineering
decides how it is quantified. This package only acquires visual evidence.
"""
from __future__ import annotations

from .config import GATE_VERSION, MODEL_VERSION, PHASE_ID, PHASE_NAME

__all__ = [
    "GATE_VERSION",
    "MODEL_VERSION",
    "PHASE_ID",
    "PHASE_NAME",
]
