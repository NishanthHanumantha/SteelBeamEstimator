"""Side-face reinforcement detector. MODEL_VERSION: 8.4.0"""
from __future__ import annotations

from typing import Any, Dict, List

MODEL_VERSION = "8.4.0"


class SideFaceReinforcementDetector:
    """Detect side-face / web / skin reinforcement."""

    def detect(self, intent: Any, depth_mm: float = 750.0) -> Dict[str, Any]:
        role = str(getattr(intent, "role", "") or "")
        layer = str(getattr(intent, "layer", "") or "")
        dia = float(getattr(intent, "diameter_mm", 0) or 0)
        evidence: List[str] = []

        if role == "SIDE_FACE_REINFORCEMENT" or layer == "SIDE":
            evidence.append("role_or_layer_side")
            return {"side_face": True, "confidence": 0.92, "evidence": evidence}

        if (
            depth_mm >= 900
            and layer in ("MID", "")
            and dia <= 16
            and role
            not in (
                "TOP_MAIN",
                "BOTTOM_MAIN",
                "STIRRUP",
                "TOP_EXTRA",
                "BOTTOM_EXTRA",
            )
        ):
            evidence.append("deep_beam_mid_small_dia")
            return {"side_face": True, "confidence": 0.65, "evidence": evidence}

        evidence.append("not_side_face")
        return {"side_face": False, "confidence": 0.8, "evidence": evidence}
