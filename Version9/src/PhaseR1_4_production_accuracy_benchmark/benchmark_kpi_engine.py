"""
KPI engine — 12 production accuracy KPIs + weighted overall.
MODEL_VERSION: 8.6.0
"""
from __future__ import annotations

from typing import Any, Dict

MODEL_VERSION = "8.6.0"

# Weights sum to 1.0 — steel / classification / beam detection emphasized
_WEIGHTS = {
    "KPI_1_overall_steel_accuracy": 0.14,
    "KPI_2_diameter_accuracy": 0.10,
    "KPI_3_beam_detection_accuracy": 0.10,
    "KPI_4_beam_geometry_accuracy": 0.06,
    "KPI_5_reinforcement_classification_accuracy": 0.12,
    "KPI_6_piece_generation_accuracy": 0.08,
    "KPI_7_engineeringbar_accuracy": 0.08,
    "KPI_8_cut_length_accuracy": 0.08,
    "KPI_9_steel_weight_accuracy": 0.08,
    "KPI_10_bbs_accuracy": 0.06,
    "KPI_11_workbook_accuracy": 0.04,
}


class BenchmarkKPIEngine:
    def compute(self, comparison: Dict[str, Any]) -> Dict[str, Any]:
        beam = comparison.get("beam_accuracy") or {}
        reinf = comparison.get("reinforcement_accuracy") or {}
        piece = comparison.get("piece_accuracy") or {}
        ebar = comparison.get("engineeringbar_accuracy") or {}
        steel = comparison.get("steel_accuracy") or {}
        bbs = comparison.get("bbs_accuracy") or {}
        wb = comparison.get("workbook_accuracy") or {}

        kpis = {
            "KPI_1_overall_steel_accuracy": float(steel.get("overall_steel_score") or 0.0),
            "KPI_2_diameter_accuracy": float(steel.get("diameter_accuracy") or 0.0),
            "KPI_3_beam_detection_accuracy": float(beam.get("detection_f1") or 0.0),
            "KPI_4_beam_geometry_accuracy": float(beam.get("geometry_accuracy") or 0.0),
            "KPI_5_reinforcement_classification_accuracy": float(
                reinf.get("classification_accuracy") or 0.0
            ),
            "KPI_6_piece_generation_accuracy": float(piece.get("piece_generation_score") or 0.0),
            "KPI_7_engineeringbar_accuracy": float(ebar.get("engineeringbar_score") or 0.0),
            "KPI_8_cut_length_accuracy": float(steel.get("cut_length_accuracy") or 0.0),
            "KPI_9_steel_weight_accuracy": float(steel.get("weight_accuracy") or 0.0),
            "KPI_10_bbs_accuracy": float(bbs.get("bbs_score") or 0.0),
            "KPI_11_workbook_accuracy": float(wb.get("workbook_score") or 0.0),
        }

        overall = sum(kpis[k] * _WEIGHTS[k] for k in _WEIGHTS)
        # renormalize if some KPIs are informational zeros due to missing production pieces cut lengths
        kpis["KPI_12_overall_production_accuracy"] = round(overall, 4)

        scorecard = {
            "model_version": MODEL_VERSION,
            "kpis_pct": {k: round(v * 100.0, 2) for k, v in kpis.items()},
            "weights": _WEIGHTS,
            "overall_pct": round(overall * 100.0, 2),
            "band": self._band(overall),
        }
        return {
            "model_version": MODEL_VERSION,
            "kpis": kpis,
            "scorecard": scorecard,
        }

    @staticmethod
    def _band(score: float) -> str:
        if score >= 0.85:
            return "PRODUCTION_READY"
        if score >= 0.70:
            return "NEAR_READY"
        if score >= 0.50:
            return "NEEDS_IMPROVEMENT"
        return "CRITICAL_GAP"
