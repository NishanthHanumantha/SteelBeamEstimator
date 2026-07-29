"""
General Notes adapter — consume existing Engineering Context only.
MODEL_VERSION: 8.8.1
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

MODEL_VERSION = "8.8.1"


class GeneralNotesAdapter:
    """Read cover / hook / grades from R.2A engineering_context.json (no re-parse)."""

    def __init__(self, v8_root: Path):
        self.v8 = Path(v8_root)
        self.path = (
            self.v8 / "data" / "output" / "PhaseR.2A_engineering_context" / "engineering_context.json"
        )
        self._data: Dict[str, Any] = {}
        if self.path.exists():
            self._data = json.loads(self.path.read_text(encoding="utf-8"))

    @property
    def available(self) -> bool:
        return bool(self._data)

    def clear_cover_mm(self, element: str = "BEAM") -> float:
        rules = self._data.get("cover_rules") or []
        # Prefer BEAM IN SUPERSTRUCTURE, then any BEAM
        preferred = []
        for r in rules:
            el = str(r.get("element") or "").upper()
            if "BEAM" in el and "PLINTH" not in el:
                preferred.append(r)
        if preferred:
            # exact superstructure first
            for r in preferred:
                if "SUPERSTRUCTURE" in str(r.get("element") or "").upper():
                    return float(r.get("cover_mm") or 0)
            return float(preferred[0].get("cover_mm") or 0)
        for r in rules:
            if "BEAM" in str(r.get("element") or "").upper():
                return float(r.get("cover_mm") or 0)
        fb = self._data.get("fallback_cover_mm")
        if fb is not None:
            return float(fb)
        raise RuntimeError("Clear cover not available in General Notes model")

    def hook_rules(self) -> List[Dict[str, Any]]:
        return list(self._data.get("hook_rules") or [])

    def primary_hook_rule(self, prefer_angle: int = 135) -> Dict[str, Any]:
        rules = self.hook_rules()
        for r in rules:
            if int(r.get("angle_deg") or 0) == prefer_angle:
                return r
        if rules:
            return rules[0]
        raise RuntimeError("Hook rules not available in General Notes model")

    def steel_grade(self) -> str:
        return str(self._data.get("primary_steel_grade") or self._data.get("fallback_steel_grade") or "")

    def summary(self) -> Dict[str, Any]:
        return {
            "source": str(self.path) if self.path.exists() else None,
            "available": self.available,
            "clear_cover_mm": self.clear_cover_mm() if self.available else None,
            "hook_rules": self.hook_rules(),
            "steel_grade": self.steel_grade(),
            "fallback_cover_mm": self._data.get("fallback_cover_mm"),
        }
