"""
Hook engine — lengths from General Notes (xd multipliers), never hardcoded.
MODEL_VERSION: 8.8.1
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from general_notes_adapter import GeneralNotesAdapter
from stirrup_model import HookResult

MODEL_VERSION = "8.8.1"


class HookEngine:
    def __init__(self, gn: GeneralNotesAdapter):
        self._gn = gn

    def compute(self, diameter_mm: float, prefer_angle: int = 135) -> HookResult:
        if diameter_mm <= 0:
            raise ValueError("diameter_mm must be > 0")
        rule = self._gn.primary_hook_rule(prefer_angle=prefer_angle)
        mult = int(rule.get("multiplier_xd") or 0)
        if mult <= 0:
            raise RuntimeError("Hook multiplier_xd missing/invalid in General Notes")
        angle = int(rule.get("angle_deg") or prefer_angle)
        hook_len = float(mult) * float(diameter_mm)
        return HookResult(
            hook_length_mm=hook_len,
            hook_type=str(rule.get("rule_type") or f"HOOK_{mult}XD"),
            hook_angle_deg=angle,
            multiplier_xd=mult,
            source=str(rule.get("source") or "GeneralNotes"),
        )
