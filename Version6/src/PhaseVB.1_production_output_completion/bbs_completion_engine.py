"""
BBS Completion Engine — Phase V.B.1 MODULE 3

Generates full estimator-style Bar Bending Schedule rows from L.2 data + steel weights.
Each beam contains rows for all bar roles per specification.
Every engineering object appears as its own row.
"""
import math
from typing import List, Dict, Any, Optional

from production_output_models import BBSRow, BeamSteelWeight, ProjectSteelSummary

_FRAME_TYPE = "TF"

_ROLE_DISPLAY = {
    "TOP_MAIN":    "Top bars",
    "BOTTOM_MAIN": "Bottom bars",
    "TOP_EXTRA":   "Top bars - Extra",
    "BOTTOM_EXTRA":"Bottom bars - Extra",
    "SIDE_FACE":   "SFR",
    "STIRRUP":     "Stirrups",
    "SPACER":      "Spacer bars",
    "BENT":        "Bent bars",
    "CRANKED":     "Cranked bars",
    "DEVELOPMENT": "Dev. length bars",
    "LAP":         "Lap bars",
}

_SUPPORTED_DIAMETERS = [8, 10, 12, 16, 20, 25, 32]


class BBSCompletionEngine:
    """
    Converts ProjectSteelSummary into a flat list of BBSRow objects that
    mirror the estimator workbook layout.
    """

    def __init__(self, summary: ProjectSteelSummary) -> None:
        self.summary = summary

    def generate(self) -> List[BBSRow]:
        rows: List[BBSRow] = []
        si = 1
        for bw in self.summary.beam_weights:
            # ── Beam header row ──────────────────────────────────────
            rows.append(BBSRow(
                si_no=si,
                frame_type=_FRAME_TYPE,
                description=bw.beam_id,
                diameter_mm=1,                    # member count
                spacing_m=round(bw.span_mm / 1000, 3) if bw.span_mm else None,
                quantity=int(bw.width_mm) if bw.width_mm else None,
                dvlp_length_m=bw.depth_mm / 1000 if bw.depth_mm else None,
                cut_length_m=None,
                total_length_m=None,
                total_weight_kg=bw.total_weight_kg,
                is_beam_header=True,
                beam_id=bw.beam_id,
            ))
            si += 1

            # Group bars by role to produce one row per bar group
            role_groups: Dict[str, List[Any]] = {}
            for bar in bw.bar_weights:
                role_groups.setdefault(bar.role, []).append(bar)

            role_order = [
                "TOP_MAIN", "TOP_EXTRA", "BOTTOM_MAIN", "BOTTOM_EXTRA",
                "SIDE_FACE", "STIRRUP", "SPACER", "BENT", "CRANKED",
                "DEVELOPMENT", "LAP",
            ]

            for role in role_order:
                bars = role_groups.get(role, [])
                for bar in bars:
                    # Build per-diameter weight columns
                    dw: Dict[int, Optional[float]] = {d: None for d in _SUPPORTED_DIAMETERS}
                    d_key = int(bar.diameter_mm)
                    if d_key in dw:
                        dw[d_key] = round(bar.total_weight_kg, 3)

                    # Spacing (for stirrups, SFR)
                    spacing_m: Optional[float] = None
                    if bar.role in ("STIRRUP", "SIDE_FACE") and bar.cut_length_mm:
                        # Infer spacing from quantity and span
                        if bw.span_mm and bar.quantity and bar.quantity > 1:
                            spacing_m = round(bw.span_mm / (bar.quantity * 1000), 3)

                    rows.append(BBSRow(
                        si_no=None,
                        frame_type=_FRAME_TYPE,
                        description=_ROLE_DISPLAY.get(role, role),
                        diameter_mm=bar.diameter_mm,
                        spacing_m=spacing_m,
                        quantity=bar.quantity,
                        dvlp_length_m=round(
                            bar.cut_length_mm / 1000 - bw.span_mm / 1000, 3
                        ) if bar.cut_length_mm and bw.span_mm else None,
                        cut_length_m=round(bar.cut_length_mm / 1000, 3),
                        total_length_m=round(
                            bar.cut_length_mm * bar.quantity / 1000, 3
                        ),
                        weight_d8=dw[8],
                        weight_d10=dw[10],
                        weight_d12=dw[12],
                        weight_d16=dw[16],
                        weight_d20=dw[20],
                        weight_d25=dw[25],
                        weight_d32=dw[32],
                        total_weight_kg=round(bar.total_weight_kg, 3),
                        is_beam_header=False,
                        beam_id=bw.beam_id,
                    ))

        return rows

    def diameter_totals(self, rows: List[BBSRow]) -> Dict[int, float]:
        totals: Dict[int, float] = {d: 0.0 for d in _SUPPORTED_DIAMETERS}
        for row in rows:
            if not row.is_beam_header:
                for d, attr in [
                    (8, "weight_d8"), (10, "weight_d10"), (12, "weight_d12"),
                    (16, "weight_d16"), (20, "weight_d20"), (25, "weight_d25"),
                    (32, "weight_d32"),
                ]:
                    val = getattr(row, attr, None)
                    if val:
                        totals[d] += val
        return totals
