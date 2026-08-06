"""
Cut length engine.
MODEL_VERSION: 8.8.1

Cut Length = Perimeter + Hook1 + Hook2
(identical hooks → Perimeter + 2 × Hook Length)
"""
from __future__ import annotations

from stirrup_model import HookResult

MODEL_VERSION = "8.8.1"


class CutLengthEngine:
    def compute(
        self,
        perimeter_mm: float,
        hook: HookResult,
        hook_count: int = 2,
    ) -> float:
        if perimeter_mm <= 0:
            raise ValueError("perimeter_mm must be > 0")
        if hook_count < 0:
            raise ValueError("hook_count must be >= 0")
        return float(perimeter_mm) + float(hook.hook_length_mm) * float(hook_count)
