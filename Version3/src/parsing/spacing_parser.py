"""Spacing list interpretation for stirrup annotations."""

from typing import List, Literal

SpacingMode = Literal["uniform", "variable", "alternating", "unknown"]


def spacing_mode(spacing_mm: List[int]) -> SpacingMode:
    if not spacing_mm:
        return "unknown"
    if len(spacing_mm) == 1:
        return "uniform"
    if len(spacing_mm) == 2:
        return "alternating"
    if len(spacing_mm) >= 3:
        return "variable"
    return "unknown"
