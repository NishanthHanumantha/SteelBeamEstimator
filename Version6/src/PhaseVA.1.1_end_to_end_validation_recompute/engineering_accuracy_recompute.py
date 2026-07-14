"""
Phase V.A.1.1 — engineering_accuracy_recompute.py
Recalculates all engineering KPIs from V.B.1 production output JSON artefacts.
No engineering logic is re-implemented — only reads and aggregates existing outputs.
MODEL_VERSION: 6.6.3
"""
from __future__ import annotations

import json
import pathlib
from typing import Dict, Optional

from validation_recompute_models import EngineeringAccuracyKPIs

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_OUT  = _ROOT / "Version6/data/output/Production_Output"

_ENGINEERING_TOTALS  = _OUT / "engineering_totals.json"
_BBS_SUMMARY         = _OUT / "bbs_summary.json"
_STEEL_WEIGHT_SUMM   = _OUT / "steel_weight_summary.json"
_PROD_STATS          = _OUT / "production_statistics.json"

# SI.1 artefact — stirrup per-beam detail
_SI1_STATS = (
    _ROOT
    / "Version6/data/output/PhaseSI.1_stirrup_improvement/stirrup_statistics.json"
)
# SI.0 artefact — recovery summary
_SI0_SUMM = (
    _ROOT
    / "Version6/data/output/PhaseSI.0_stirrup_recovery/phase_si0_summary.json"
)


def _load(path: pathlib.Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


class EngineeringAccuracyRecompute:
    """
    Reads V.B.1 / SI.0 / SI.1 JSON artefacts and builds updated KPI object.
    """

    def compute(self, workbook_match_pct: float = 0.0) -> EngineeringAccuracyKPIs:
        totals   = _load(_ENGINEERING_TOTALS)
        bbs      = _load(_BBS_SUMMARY)
        sw       = _load(_STEEL_WEIGHT_SUMM)
        stats    = _load(_PROD_STATS)
        si1      = _load(_SI1_STATS)
        si0      = _load(_SI0_SUMM)

        total_beams          = int(totals.get("total_beams", 0))
        total_engineering_rows = int(totals.get("total_engineering_rows", 0))
        total_steel_kg       = float(totals.get("total_steel_kg", 0.0))
        total_bbs_rows       = int(stats.get("total_bbs_rows", 0))

        # Diameter breakdown
        raw_diam: Dict = totals.get("diameter_totals_kg", {})
        diameter_totals_kg: Dict[str, float] = {}
        diam_label_map = {
            8: "Y8", 10: "Y10", 12: "Y12",
            16: "Y16", 20: "Y20", 25: "Y25", 32: "Y32",
        }
        for k, v in raw_diam.items():
            label = diam_label_map.get(int(k), f"Y{k}")
            diameter_totals_kg[label] = round(float(v), 3)

        # Stirrup coverage — beams where SI.1 processed stirrups
        stirrup_beams = int(si1.get("total_beams_with_stirrups", 0))

        # Bar-type coverage: read from BBS summary beam detail
        beams_with_top      = 0
        beams_with_bottom   = 0
        beams_with_extra    = 0
        beams_with_dev      = 0
        beams_with_lap      = 0
        beams_with_spacer   = 0

        beam_details: list = bbs.get("beams", [])
        for beam_detail in beam_details:
            rows_by_role = beam_detail.get("roles", {})
            if rows_by_role.get("TOP_BAR") or rows_by_role.get("top_bar"):
                beams_with_top += 1
            if rows_by_role.get("BOTTOM_BAR") or rows_by_role.get("bottom_bar"):
                beams_with_bottom += 1
            if rows_by_role.get("EXTRA_BAR") or rows_by_role.get("extra_bar"):
                beams_with_extra += 1
            if rows_by_role.get("DEVELOPMENT") or rows_by_role.get("development"):
                beams_with_dev += 1
            if rows_by_role.get("LAP_BAR") or rows_by_role.get("lap_bar"):
                beams_with_lap += 1
            if rows_by_role.get("SPACER") or rows_by_role.get("spacer"):
                beams_with_spacer += 1

        # If BBS summary doesn't have beam-level role breakdown, use total beams
        if not beam_details:
            beams_with_top    = total_beams
            beams_with_bottom = total_beams

        # BBS completeness: generated rows vs expected estimator rows (103)
        expected_bbs_rows = 103
        bbs_completeness = round(
            min(100.0, 100.0 * total_bbs_rows / expected_bbs_rows), 2
        )

        return EngineeringAccuracyKPIs(
            total_beams=total_beams,
            beams_with_top_bars=beams_with_top,
            beams_with_bottom_bars=beams_with_bottom,
            beams_with_extra_bars=beams_with_extra,
            beams_with_stirrups=stirrup_beams,
            beams_with_development_bars=beams_with_dev,
            beams_with_lap_bars=beams_with_lap,
            beams_with_spacer_bars=beams_with_spacer,
            total_engineering_rows=total_engineering_rows,
            total_bbs_rows=total_bbs_rows,
            total_steel_kg=total_steel_kg,
            diameter_totals_kg=diameter_totals_kg,
            project_total_kg=total_steel_kg,
            workbook_match_pct=workbook_match_pct,
            stirrup_coverage_beams=stirrup_beams,
            bbs_completeness_pct=bbs_completeness,
        )
