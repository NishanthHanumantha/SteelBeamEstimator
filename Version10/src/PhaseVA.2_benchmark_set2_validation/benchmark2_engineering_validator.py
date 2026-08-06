"""
Phase V.A.2 -- benchmark2_engineering_validator.py
Read Version8 production output artefacts and compute engineering KPIs.
MODEL_VERSION: 7.0.0
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, Optional

from benchmark2_models import EngineeringKPIs

_ROOT           = pathlib.Path(__file__).resolve().parents[3]
_V7             = _ROOT / "Version8"
_PRODUCTION_OUT = _V7 / "data/output/Production_Output"
_SI0_OUT        = _V7 / "data/output/PhaseSI.0_stirrup_recovery"
_SI1_OUT        = _V7 / "data/output/PhaseSI.1_stirrup_improvement"
_L2_OUT         = _V7 / "data/output/PhaseL.2 - engineering_reinforcement_interpretation"


def _load_json(path: pathlib.Path) -> Optional[Any]:
    if not path.exists() or path.stat().st_size < 3:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


class Benchmark2EngineeringValidator:
    """
    Read production output JSON files and derive engineering KPIs
    for Benchmark Set 2 without modifying any engineering logic.
    """

    def compute_kpis(self) -> EngineeringKPIs:
        prod_stats    = _load_json(_PRODUCTION_OUT / "production_statistics.json") or {}
        eng_totals    = _load_json(_PRODUCTION_OUT / "engineering_totals.json") or {}
        steel_summary = _load_json(_PRODUCTION_OUT / "steel_weight_summary.json") or {}
        bbs_summary   = _load_json(_PRODUCTION_OUT / "bbs_summary.json") or {}
        si1_data      = _load_json(_SI1_OUT / "stirrup_improvement_report.json") or {}
        l2_data       = _load_json(_L2_OUT / "beam_reinforcement_models.json") or {}

        # Beam count
        total_beams = (
            prod_stats.get("total_beams")
            or eng_totals.get("total_beams")
            or len(l2_data.get("beams", {}))
            or 0
        )

        # Engineering rows (BBS rows)
        total_engineering_rows = (
            bbs_summary.get("total_rows")
            or prod_stats.get("total_bbs_rows")
            or 0
        )
        total_bbs_rows = total_engineering_rows

        # Total steel
        total_steel_kg = (
            steel_summary.get("total_weight_kg")
            or eng_totals.get("total_weight_kg")
            or prod_stats.get("total_steel_kg")
            or 0.0
        )

        # Stirrup coverage
        stirrup_coverage_beams = (
            si1_data.get("stirrup_coverage", {}).get("beams_with_stirrups")
            or bbs_summary.get("beams_with_stirrups")
            or prod_stats.get("beams_with_stirrups")
            or 0
        )

        # BBS completeness
        bbs_completeness_pct = (
            bbs_summary.get("completeness_pct")
            or prod_stats.get("bbs_completeness_pct")
            or (round(100 * total_bbs_rows / (total_beams * 5), 1) if total_beams else 0.0)
        )

        # Diameter totals (kg per bar diameter)
        dia_totals: Dict[str, float] = {}
        raw_dia = (
            steel_summary.get("diameter_totals")
            or eng_totals.get("diameter_totals")
            or {}
        )
        if isinstance(raw_dia, dict):
            for k, v in raw_dia.items():
                try:
                    dia_totals[str(k)] = float(v)
                except (TypeError, ValueError):
                    pass

        return EngineeringKPIs(
            total_beams=int(total_beams),
            total_engineering_rows=int(total_engineering_rows),
            total_bbs_rows=int(total_bbs_rows),
            total_steel_kg=round(float(total_steel_kg), 2),
            stirrup_coverage_beams=int(stirrup_coverage_beams),
            bbs_completeness_pct=round(float(bbs_completeness_pct), 1),
            diameter_totals_kg=dia_totals,
            data_source="Version8/data/output/Production_Output",
        )
