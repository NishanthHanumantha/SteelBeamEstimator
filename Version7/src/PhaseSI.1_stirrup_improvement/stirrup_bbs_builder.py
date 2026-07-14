"""
BBS Builder — Phase SI.1 MODULE 5

Converts StirrupGroup objects into estimator-style BBS row dictionaries
that are consumed by Phase V.B.1's EstimatorExcelGenerator.

Produces exactly ONE dict per StirrupGroup (one BBS row per merged group).
"""
import math
from typing import List, Dict, Any, Optional

from stirrup_models import StirrupGroup, StirrupType

_SUPPORTED_DIAMETERS = [8, 10, 12, 16, 20, 25, 32]


def group_to_bbs_dict(
    group: StirrupGroup,
    beam_id: str,
    frame_type: str = "TF",
) -> Dict[str, Any]:
    """
    Converts one StirrupGroup to a BBS row dictionary matching
    the keys expected by Phase V.B.1's BBSRow dataclass.
    """
    d = int(group.diameter_mm)

    # Spacing in metres — for merged support groups, use the common spacing
    spacing_m = round(group.spacing_mm / 1000, 3)

    # Development length = cut_length - effective span (estimator style)
    # For stirrups: dvlp = hook allowance (2 × 10d)
    hook_mm = 2 * 10 * group.diameter_mm
    dvlp_m = round(hook_mm / 1000, 3)

    cut_m = round(group.cut_length_mm / 1000, 3)
    total_len_m = round(group.cut_length_mm * group.quantity / 1000, 3)

    # Per-diameter weight columns
    dw: Dict[str, Optional[float]] = {
        "weight_d8":  None,
        "weight_d10": None,
        "weight_d12": None,
        "weight_d16": None,
        "weight_d20": None,
        "weight_d25": None,
        "weight_d32": None,
    }
    col_map = {8: "weight_d8", 10: "weight_d10", 12: "weight_d12",
               16: "weight_d16", 20: "weight_d20", 25: "weight_d25", 32: "weight_d32"}
    if d in col_map:
        dw[col_map[d]] = round(group.total_weight_kg, 3)

    # Description: "Stirrups" + merge note if merged
    desc = "Stirrups"
    if group.is_merged:
        desc = "Stirrups (Sup.)"
    elif any(z.role.value == "MIDSPAN" for z in group.zones):
        desc = "Stirrups (Mid.)"

    return {
        "si_no": None,
        "frame_type": frame_type,
        "description": desc,
        "diameter_mm": group.diameter_mm,
        "spacing_m": spacing_m,
        "quantity": group.quantity,
        "dvlp_length_m": dvlp_m,
        "cut_length_m": cut_m,
        "total_length_m": total_len_m,
        **dw,
        "total_weight_kg": round(group.total_weight_kg, 3),
        "is_beam_header": False,
        "beam_id": beam_id,
    }


class StirrupBBSBuilder:
    """Converts a list of StirrupGroups to BBS row dictionaries."""

    def build(
        self,
        groups: List[StirrupGroup],
        beam_id: str,
        frame_type: str = "TF",
    ) -> List[Dict[str, Any]]:
        return [group_to_bbs_dict(g, beam_id, frame_type) for g in groups]
