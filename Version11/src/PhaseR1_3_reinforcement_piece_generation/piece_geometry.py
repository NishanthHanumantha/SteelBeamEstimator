"""
Piece geometry / cut-length from GeometryProvider — never invent span.
MODEL_VERSION: 8.5.0
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "8.5.0"
_DENSITY = 7850.0


class PieceGeometry:
    """Deterministic cut length using GeometryProvider span + detailing Ld/hooks."""

    def cut_length(
        self,
        span_mm: Optional[float],
        development_length_mm: Optional[int],
        hook_multiple: Optional[float],
        diameter_mm: float,
        piece_start_mm: Optional[float],
        piece_end_mm: Optional[float],
        fabrication_type: str,
        role: str,
        depth_mm: Optional[float] = None,
        width_mm: Optional[float] = None,
    ) -> Tuple[Optional[float], List[str], List[str]]:
        """
        Returns (cut_length_mm, evidence, validation_flags).
        Never fabricates span — flags if geometry unavailable.
        """
        evidence: List[str] = []
        flags: List[str] = []

        if role == "STIRRUP" or "STIRRUP" in str(fabrication_type).upper():
            return self._stirrup_cut(
                diameter_mm, depth_mm, width_mm, piece_start_mm, piece_end_mm,
                evidence, flags,
            )

        # Longitudinal: prefer explicit piece extents when both known
        if piece_start_mm is not None and piece_end_mm is not None:
            base = max(0.0, float(piece_end_mm) - float(piece_start_mm))
            evidence.append(f"piece_extent={piece_start_mm}->{piece_end_mm}")
        elif span_mm is not None and span_mm > 0:
            base = float(span_mm)
            evidence.append(f"clear_span_mm={span_mm}")
        else:
            flags.append("geometry_span_unavailable")
            evidence.append("cut_length_not_fabricated")
            return None, evidence, flags

        ld = float(development_length_mm) if development_length_mm is not None else None
        if ld is None:
            flags.append("development_length_unavailable_for_cut")
            evidence.append("ld_not_added")
            ld_add = 0.0
        else:
            ld_add = 2.0 * ld
            evidence.append(f"2*Ld={ld_add}")

        hook_add = 0.0
        if hook_multiple is not None and diameter_mm > 0:
            hook_add = 2.0 * float(hook_multiple) * float(diameter_mm)
            evidence.append(f"2*hook={hook_add}")
        else:
            evidence.append("hook_not_added")

        cut = base + ld_add + hook_add
        evidence.append(f"cut_length_mm={cut}")
        return round(cut, 1), evidence, flags

    def _stirrup_cut(
        self,
        diameter_mm: float,
        depth_mm: Optional[float],
        width_mm: Optional[float],
        start: Optional[float],
        end: Optional[float],
        evidence: List[str],
        flags: List[str],
    ) -> Tuple[Optional[float], List[str], List[str]]:
        if depth_mm is None or width_mm is None or depth_mm <= 0 or width_mm <= 0:
            flags.append("stirrup_section_geometry_unavailable")
            evidence.append("stirrup_cut_not_fabricated")
            return None, evidence, flags
        # Closed loop perimeter + hooks (10db each end typical)
        cut = 2.0 * (float(depth_mm) + float(width_mm)) + 20.0 * float(diameter_mm)
        evidence.append(f"stirrup_perimeter_cut={cut}")
        if start is not None and end is not None:
            evidence.append(f"zone_extent={start}->{end}")
        return round(cut, 1), evidence, flags

    @staticmethod
    def weight_kg(diameter_mm: float, cut_mm: Optional[float], quantity: int) -> Optional[float]:
        if cut_mm is None or diameter_mm <= 0 or quantity <= 0:
            return None
        area = math.pi * diameter_mm * diameter_mm / 4.0
        return round(area * cut_mm * quantity * _DENSITY / 1e9, 4)
