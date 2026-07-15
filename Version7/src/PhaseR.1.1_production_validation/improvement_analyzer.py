"""
improvement_analyzer.py — Analyse improvement vs previous V.RUN.1 output.

Reports:
  - Newly covered beams (improvement)
  - Beams that changed significantly
  - Diameter-level changes
  - Overall coverage gain
  - Engineering recommendation
"""

from __future__ import annotations

import logging
from typing import Dict, List

log = logging.getLogger(__name__)


class ImprovementAnalyzer:
    """Classifies each beam as improvement, regression, or unchanged."""

    def analyze(
        self,
        comparison: dict,
        statistics: dict,
    ) -> dict:
        beam_rows = comparison.get("beam_comparison", [])
        dia_rows  = comparison.get("diameter_comparison", [])
        coverage  = comparison.get("coverage_improvement", {})

        improvements = [r for r in beam_rows if r["status"] == "NEW_DATA"]
        regressions  = [r for r in beam_rows if r["status"] == "LOST_DATA"]
        increased    = [r for r in beam_rows if r["status"] == "INCREASED"]
        decreased    = [r for r in beam_rows if r["status"] == "DECREASED"]
        unchanged    = [r for r in beam_rows if r["status"] == "UNCHANGED"]

        # Top 5 by magnitude
        top_new   = sorted(improvements, key=lambda r: r["new_kg"], reverse=True)[:5]
        top_incr  = sorted(increased,   key=lambda r: abs(r["diff_kg"]), reverse=True)[:5]
        top_decr  = sorted(decreased,   key=lambda r: abs(r["diff_kg"]), reverse=True)[:5]

        # Diameter-level improvement: diameters newly appearing
        prev_no_dia = [d for d in dia_rows if d["prev_kg"] == 0 and d["new_kg"] > 0]
        lost_dia    = [d for d in dia_rows if d["new_kg"] == 0 and d["prev_kg"] > 0]

        # Verdict
        coverage_gain = float(statistics.get("coverage_improvement_pct", 0))
        if coverage_gain >= 50:
            verdict = "MAJOR_IMPROVEMENT"
            recommendation = (
                f"Phase R.1 DXF discovery increased beam coverage by {coverage_gain:.1f} percentage points. "
                "This represents a transformational improvement. "
                "Proceed to test on Benchmark Set 3 drawings."
            )
        elif coverage_gain >= 20:
            verdict = "SIGNIFICANT_IMPROVEMENT"
            recommendation = (
                f"Phase R.1 increased coverage by {coverage_gain:.1f}pp. "
                "Significant improvement achieved. Consider Phase R.2 for semantic interpretation refinement."
            )
        elif coverage_gain >= 5:
            verdict = "MODERATE_IMPROVEMENT"
            recommendation = (
                "Moderate improvement in coverage. Phase R.2 should target the remaining uncovered beams."
            )
        else:
            verdict = "MARGINAL_IMPROVEMENT"
            recommendation = "Limited coverage improvement. Phase R.2 is recommended."

        log.info("ImprovementAnalyzer: verdict=%s, coverage_gain=%.1f%%", verdict, coverage_gain)

        return {
            "verdict":           verdict,
            "recommendation":    recommendation,
            "coverage_gain_pct": coverage_gain,
            "beam_counts": {
                "newly_covered":   len(improvements),
                "increased":       len(increased),
                "decreased":       len(decreased),
                "unchanged":       len(unchanged),
                "regressions":     len(regressions),
            },
            "top_newly_covered_beams": [
                {"beam_id": r["beam_id"], "new_kg": r["new_kg"]}
                for r in top_new
            ],
            "top_increased_beams": [
                {"beam_id": r["beam_id"], "diff_kg": r["diff_kg"], "pct": r["pct_diff"]}
                for r in top_incr
            ],
            "top_decreased_beams": [
                {"beam_id": r["beam_id"], "diff_kg": r["diff_kg"], "pct": r["pct_diff"]}
                for r in top_decr
            ],
            "diameter_improvements": [
                {"diameter_mm": d["diameter_mm"], "new_kg": d["new_kg"]}
                for d in prev_no_dia
            ],
            "diameter_regressions": [
                {"diameter_mm": d["diameter_mm"], "prev_kg": d["prev_kg"]}
                for d in lost_dia
            ],
        }
