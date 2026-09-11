"""
Phase W.5 — Production Hybrid shadow adapter.

Shadow-only integration of the existing D.1–D.2 semantic hybrid path and
E.2 live Claude Vision caller. Deterministic Excel / BBS remain authoritative.
"""
from __future__ import annotations

from .config import GATE_VERSION, MODEL_VERSION, PHASE_ID, PHASE_NAME, PRODUCTION_WRITE

__all__ = [
    "GATE_VERSION",
    "MODEL_VERSION",
    "PHASE_ID",
    "PHASE_NAME",
    "PRODUCTION_WRITE",
]
