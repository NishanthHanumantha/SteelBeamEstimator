"""Piece quantity helpers. MODEL_VERSION: 8.5.0"""
from __future__ import annotations

from typing import Any

MODEL_VERSION = "8.5.0"


class PieceQuantity:
    """Deterministic quantity inheritance from detail / segment."""

    @staticmethod
    def from_detail(detail: Any) -> int:
        q = int(getattr(detail, "quantity", 0) or 0)
        return max(q, 1)

    @staticmethod
    def from_segment(seg: dict, fallback: int = 1) -> int:
        q = int(seg.get("quantity") or 0)
        return max(q, fallback)
