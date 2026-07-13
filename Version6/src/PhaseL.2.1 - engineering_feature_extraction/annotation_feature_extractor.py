"""
Annotation Feature Extractor — properties from the reinforcement annotation text.
Observations only. No semantic meaning assigned.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from engineering_feature_model import AnnotationFeatures

# Annotation priority rules (purely observational)
_HIGH_PRIORITY_LAYERS = {"-STR-REINF", "-STR-TEXT", "0"}
_HOOK_PATTERNS = re.compile(r"H|HOOK|BENT|CRANK", re.I)


class AnnotationFeatureExtractor:
    """Extract annotation observations from bar label and metadata."""

    def extract(
        self,
        bar: Dict[str, Any],
        beam_model: Dict[str, Any],
    ) -> AnnotationFeatures:
        label = bar.get("bar_label") or ""
        dia = bar.get("diameter_mm")
        qty = bar.get("quantity")
        spacing = bar.get("spacing_mm")
        grade = bar.get("steel_grade") or "Y"

        # Parse label for hook indicators
        has_hook = bool(_HOOK_PATTERNS.search(label))

        # Reconstruct callout from available data
        callout = label if label else self._reconstruct_callout(qty, grade, dia, spacing)

        # Annotation layer (from engineering object type — observational)
        eng_zone = bar.get("position_zone") or ""
        layer = "-STR-REINF" if eng_zone != "UNKNOWN_ZONE" else None

        # Priority: bars with leader (recovery data) or known spec → HIGH
        annotation_priority = "HIGH" if dia and qty else ("MEDIUM" if dia or qty else "LOW")

        return AnnotationFeatures(
            callout=callout,
            diameter_mm=float(dia) if dia is not None else None,
            quantity=int(qty) if qty is not None else None,
            spacing_mm=float(spacing) if spacing is not None else None,
            has_hook_symbol=has_hook,
            leader_count=1 if dia else 0,  # most bars have at least one leader
            leader_direction="DOWN",        # typical for top bar annotations
            leader_length_mm=None,
            annotation_layer=layer,
            annotation_style="STANDARD",
            annotation_priority=annotation_priority,
        )

    @staticmethod
    def _reconstruct_callout(
        qty: Optional[int],
        grade: str,
        dia: Optional[float],
        spacing: Optional[float],
    ) -> Optional[str]:
        if not dia:
            return None
        q = str(qty) if qty else "?"
        d = str(int(dia))
        base = f"{q}{grade}{d}"
        if spacing:
            base += f"@{int(spacing)}"
        return base
