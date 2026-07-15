"""
accuracy_statistics.py — Engineering accuracy statistics.

Computes RMSE, MAE, MAPE, overall accuracy, beam accuracy, and diameter accuracy
by comparing the new R.1.1 output against the previous V.RUN.1 baseline.

Note: Without an external validated benchmark (e.g. hand-calculated reference),
we compare against the previous best estimate.  Coverage statistics measure how
many beams now receive reinforcement vs before.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


def _rmse(errors: List[float]) -> float:
    if not errors:
        return 0.0
    return round(math.sqrt(sum(e ** 2 for e in errors) / len(errors)), 3)


def _mae(errors: List[float]) -> float:
    if not errors:
        return 0.0
    return round(sum(abs(e) for e in errors) / len(errors), 3)


def _mape(actuals: List[float], predictions: List[float]) -> float:
    """Mean Absolute Percentage Error — only for non-zero actuals."""
    pairs = [(a, p) for a, p in zip(actuals, predictions) if a > 0]
    if not pairs:
        return 0.0
    return round(sum(abs(a - p) / a * 100 for a, p in pairs) / len(pairs), 2)


class AccuracyStatistics:
    """Compute comprehensive accuracy metrics for R.1.1 vs previous output."""

    def compute(self, comparison: dict) -> dict:
        overall       = comparison.get("overall", {})
        beam_rows     = comparison.get("beam_comparison", [])
        dia_rows      = comparison.get("diameter_comparison", [])
        coverage_info = comparison.get("coverage_improvement", {})

        # Beam-level stats (using previous output as "reference")
        prev_kgs = [r["prev_kg"] for r in beam_rows]
        new_kgs  = [r["new_kg"]  for r in beam_rows]
        errors   = [n - p for n, p in zip(new_kgs, prev_kgs)]

        # Exclude beams where both are 0 (no data either side)
        active_errors = [e for n, p, e in zip(new_kgs, prev_kgs, errors) if n > 0 or p > 0]

        beam_rmse = _rmse(active_errors)
        beam_mae  = _mae(active_errors)
        beam_mape = _mape(prev_kgs, new_kgs)

        newly_covered = len(coverage_info.get("newly_covered_beams", []))
        total_beams   = len(beam_rows)
        new_coverage  = float(coverage_info.get("new_coverage_pct", 0))
        prev_coverage = float(coverage_info.get("prev_coverage_pct", 0))

        # Per-beam accuracy: % of beams within 10% of previous estimate
        within_10pct = sum(
            1 for r in beam_rows
            if r["prev_kg"] > 0 and abs(r["diff_kg"]) / r["prev_kg"] <= 0.10
        )
        total_comparable = sum(1 for r in beam_rows if r["prev_kg"] > 0)
        beam_accuracy_pct = round(100 * within_10pct / total_comparable, 1) if total_comparable else 0.0

        # Overall weight difference
        new_total  = float(overall.get("new_total_kg", 0))
        prev_total = float(overall.get("prev_total_kg", 0))
        weight_diff_pct = round(abs(new_total - prev_total) / max(prev_total, 1) * 100, 2)

        stats = {
            "overall_accuracy_pct":       round(100 - weight_diff_pct, 2),
            "overall_weight_diff_kg":     round(new_total - prev_total, 3),
            "overall_pct_error":          weight_diff_pct,
            "coverage_pct_new":           new_coverage,
            "coverage_pct_prev":          prev_coverage,
            "coverage_improvement_pct":   round(new_coverage - prev_coverage, 1),
            "newly_covered_beams":        newly_covered,
            "total_beams":                total_beams,
            "beam_accuracy_within_10pct": beam_accuracy_pct,
            "max_beam_error_kg":          round(max((abs(r["diff_kg"]) for r in beam_rows), default=0), 3),
            "min_beam_error_kg":          round(min((abs(r["diff_kg"]) for r in beam_rows if r["diff_kg"] != 0), default=0), 3),
            "avg_beam_error_kg":          round(sum(abs(e) for e in active_errors) / max(len(active_errors), 1), 3),
            "median_beam_error_kg":       _median([abs(e) for e in active_errors]),
            "rmse_kg":                    beam_rmse,
            "mae_kg":                     beam_mae,
            "mape_pct":                   beam_mape,
            "new_total_weight_kg":        new_total,
            "prev_total_weight_kg":       prev_total,
        }

        log.info(
            "AccuracyStatistics: coverage %.1f%% -> %.1f%% (+%.1f%%), RMSE=%.2f kg, MAE=%.2f kg",
            prev_coverage, new_coverage, new_coverage - prev_coverage,
            beam_rmse, beam_mae,
        )
        return stats

    @staticmethod
    def _median_of(values: List[float]) -> float:
        return _median(values)


def _median(vals: List[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    if n % 2 == 1:
        return round(s[n // 2], 3)
    return round((s[n // 2 - 1] + s[n // 2]) / 2, 3)
