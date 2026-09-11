"""Map hybrid D.4 calculations onto QA.2A BarRecord / BeamRecord objects."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP2610D4_shadow_hybrid_engineering_calculation_accuracy_benchmark.engineering_adapter import (
    map_engineering_role,
)


def _ensure_qa2a() -> None:
    p = str(Path(__file__).resolve().parents[1] / "PhaseQA.2A_ground_truth_benchmark")
    if p not in sys.path:
        sys.path.insert(0, p)


def _qa_role(engineering_role: str) -> str:
    r = str(engineering_role or "").upper()
    if r == "SPACER":
        return "SPACER_BAR"
    if r in ("SIDE_FACE", "SFR"):
        return "SIDE_FACE_REINFORCEMENT"
    return r or "UNKNOWN"


def _dia(val: Any) -> Optional[int]:
    try:
        n = int(round(float(val)))
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def hybrid_calc_to_beam(calc: Dict[str, Any]):
    _ensure_qa2a()
    from gt_models import BarRecord, BeamRecord  # type: ignore

    bid = str(calc.get("beam_id") or "")
    bars: List[Any] = []
    dia_kg: Dict[int, float] = {}
    for g in calc.get("groups") or []:
        if not isinstance(g, dict):
            continue
        if g.get("status") != "CALCULATED" or g.get("weight_kg") is None:
            continue
        role = _qa_role(g.get("engineering_role") or map_engineering_role(g.get("layer"), g.get("role")))
        dia = _dia(g.get("diameter_mm"))
        qty = float(g.get("quantity") or 0)
        kg = float(g.get("weight_kg") or 0)
        bars.append(
            BarRecord(
                beam_id=bid,
                bar_role=role,
                diameter=dia,
                quantity=qty,
                cut_length=g.get("cut_length_mm"),
                steel_weight=kg,
                source_description=f"HYBRID:{g.get('origin')}",
            )
        )
        if dia:
            dia_kg[dia] = round(dia_kg.get(dia, 0.0) + kg, 4)
    for g in (calc.get("spacers") or {}).get("groups") or []:
        if not isinstance(g, dict) or g.get("weight_kg") is None:
            continue
        dia = _dia(g.get("diameter_mm"))
        kg = float(g.get("weight_kg") or 0)
        bars.append(
            BarRecord(
                beam_id=bid,
                bar_role="SPACER_BAR",
                diameter=dia,
                quantity=float(g.get("quantity") or 0),
                cut_length=g.get("cut_length_mm"),
                steel_weight=kg,
                source_description="DETERMINISTIC_SPACER",
            )
        )
        if dia:
            dia_kg[dia] = round(dia_kg.get(dia, 0.0) + kg, 4)
    for g in (calc.get("stirrups") or {}).get("calculated_groups") or []:
        if not isinstance(g, dict) or g.get("weight_kg") is None:
            continue
        dia = _dia(g.get("diameter_mm"))
        kg = float(g.get("weight_kg") or 0)
        bars.append(
            BarRecord(
                beam_id=bid,
                bar_role="STIRRUP",
                diameter=dia,
                quantity=float(g.get("quantity") or 0),
                cut_length=g.get("cut_length_mm"),
                steel_weight=kg,
                source_description="DETERMINISTIC_STIRRUP_ENGINEERING",
            )
        )
        if dia:
            dia_kg[dia] = round(dia_kg.get(dia, 0.0) + kg, 4)
    steel = float(calc.get("hybrid_weight_kg") or sum(b.steel_weight for b in bars) or 0.0)
    return BeamRecord(
        beam_id=bid,
        steel_kg=steel,
        diameter_kg=dia_kg,
        bars=bars,
        aliases=[bid],
    )


def calcs_to_workbook(calcs: List[Dict[str, Any]], *, source_path: str):
    _ensure_qa2a()
    from gt_models import NormalizedWorkbook  # type: ignore

    beams = [hybrid_calc_to_beam(c) for c in calcs if c.get("beam_id")]
    total = round(sum(b.steel_kg for b in beams), 4)
    dia: Dict[int, float] = {}
    for b in beams:
        for d, kg in (b.diameter_kg or {}).items():
            dia[int(d)] = round(dia.get(int(d), 0.0) + float(kg), 4)
    return NormalizedWorkbook(
        source_path=source_path,
        source_label="MODEL",
        project_name="Fifth Set hybrid shadow",
        beams=beams,
        total_steel_kg=total,
        total_steel_mt=round(total / 1000.0, 4),
        diameter_kg=dia,
    )


__all__ = ["calcs_to_workbook", "hybrid_calc_to_beam"]
