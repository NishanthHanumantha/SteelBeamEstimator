"""
production_comparator.py — Compare new R.1.1 output against previous V.RUN.1 output.

Computes per-beam and per-diameter differences in steel weight.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)


def _safe_pct(a: float, b: float) -> Optional[float]:
    """Percentage difference (a - b) / b * 100. None if b == 0."""
    if b == 0:
        return None
    return round((a - b) / b * 100, 2)


class ProductionComparator:
    """Compare R.1.1 and previous V.RUN.1 steel weight summaries."""

    def compare(
        self,
        new_sw:  dict,     # R.1.1 steel_weight_summary_r1.json
        prev_sw: dict,     # Previous Production_Output/steel_weight_summary.json
    ) -> dict:
        """Return full comparison dict."""

        new_total  = float(new_sw.get("total_weight_kg", 0))
        prev_total = float(prev_sw.get("total_weight_kg", 0))

        overall = {
            "new_total_kg":          round(new_total, 3),
            "prev_total_kg":         round(prev_total, 3),
            "diff_kg":               round(new_total - prev_total, 3),
            "pct_diff":              _safe_pct(new_total, prev_total),
            "new_beams_with_weight": sum(1 for b in new_sw.get("beam_weights", []) if b.get("total_weight_kg", 0) > 0),
            "prev_beams_with_weight": sum(1 for b in prev_sw.get("beam_weights", []) if b.get("total_weight_kg", 0) > 0),
        }

        # ── Per-beam comparison ───────────────────────────────────────────────
        new_by_beam  = {b["beam_id"]: b for b in new_sw.get("beam_weights", [])}
        prev_by_beam = {b["beam_id"]: b for b in prev_sw.get("beam_weights", [])}

        all_beams = sorted(set(new_by_beam) | set(prev_by_beam))
        beam_rows: List[dict] = []
        for bid in all_beams:
            nw = float(new_by_beam.get(bid, {}).get("total_weight_kg", 0))
            pw = float(prev_by_beam.get(bid, {}).get("total_weight_kg", 0))
            diff = nw - pw
            status = (
                "NEW_DATA" if pw == 0 and nw > 0 else
                "LOST_DATA" if nw == 0 and pw > 0 else
                "UNCHANGED" if abs(diff) < 0.01 else
                "INCREASED" if diff > 0 else "DECREASED"
            )
            beam_rows.append({
                "beam_id":     bid,
                "new_kg":      round(nw, 3),
                "prev_kg":     round(pw, 3),
                "diff_kg":     round(diff, 3),
                "pct_diff":    _safe_pct(nw, pw),
                "status":      status,
            })
        beam_rows.sort(key=lambda r: abs(r["diff_kg"]), reverse=True)

        # ── Per-diameter comparison ───────────────────────────────────────────
        new_dia  = {d["diameter_mm"]: d for d in new_sw.get("diameter_summary", [])}
        prev_dia = {d["diameter_mm"]: d for d in prev_sw.get("diameter_summary", [])}
        all_dias = sorted(set(new_dia) | set(prev_dia))

        dia_rows: List[dict] = []
        for d in all_dias:
            nw = float(new_dia.get(d, {}).get("total_weight_kg", 0))
            pw = float(prev_dia.get(d, {}).get("total_weight_kg", 0))
            dia_rows.append({
                "diameter_mm": d,
                "new_kg":      round(nw, 3),
                "prev_kg":     round(pw, 3),
                "diff_kg":     round(nw - pw, 3),
                "pct_diff":    _safe_pct(nw, pw),
            })

        # ── Coverage improvement ──────────────────────────────────────────────
        coverage_improvement = {
            "prev_coverage_pct": round(100 * overall["prev_beams_with_weight"] / max(len(all_beams), 1), 1),
            "new_coverage_pct":  round(100 * overall["new_beams_with_weight"] / max(len(all_beams), 1), 1),
            "newly_covered_beams": [
                r["beam_id"] for r in beam_rows if r["status"] == "NEW_DATA"
            ],
        }

        log.info(
            "Comparator: prev=%.1f kg (%d beams), new=%.1f kg (%d beams), diff=%.1f kg",
            prev_total, overall["prev_beams_with_weight"],
            new_total,  overall["new_beams_with_weight"],
            new_total - prev_total,
        )

        return {
            "overall":              overall,
            "beam_comparison":      beam_rows,
            "diameter_comparison":  dia_rows,
            "coverage_improvement": coverage_improvement,
        }
