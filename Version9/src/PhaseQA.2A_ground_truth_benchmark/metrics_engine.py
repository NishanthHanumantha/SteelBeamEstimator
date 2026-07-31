"""
metrics_engine.py — Compute Metrics 1–8 for Ground Truth benchmark.
MODEL_VERSION: 8.9.1
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from gt_models import NormalizedWorkbook

MODEL_VERSION = "9.1.0"


def _pct(n: float, d: float) -> float:
    return round(100.0 * n / d, 2) if d else 0.0


class MetricsEngine:
    def compute(
        self,
        drawing_set: str,
        estimator: NormalizedWorkbook,
        model: NormalizedWorkbook,
        beam_matching: Dict[str, Any],
        bar_matching: Dict[str, Any],
    ) -> Dict[str, Any]:
        steel = self._steel(estimator, model)
        diameter = self._diameter(estimator, model, bar_matching)
        return {
            "model_version": MODEL_VERSION,
            "drawing_set": drawing_set,
            "metric1_beam_detection": {
                "estimator_beams": beam_matching["estimator_beams"],
                "detected_beams": beam_matching["detected_beams"],
                "undetected_beams": beam_matching["undetected_beams"],
                "detection_pct": beam_matching["detection_pct"],
            },
            "metric2_beam_matching": {
                "matched_beams": beam_matching["correctly_matched"],
                "incorrect_beams": beam_matching["incorrect_beams"],
                "matching_pct": beam_matching["matching_pct"],
            },
            "metric3_bar_detection": {
                "estimator_bars": bar_matching["estimator_bars"],
                "detected_bars": bar_matching["detected_bars"],
                "detection_pct": bar_matching["detection_pct"],
            },
            "metric4_bar_accuracy": {
                "correct_bars": bar_matching["correct_bars"],
                "detected_bars": bar_matching["detected_bars"],
                "accuracy_pct": bar_matching["accuracy_pct"],
            },
            "metric5_missing_bars": {
                "missing_bars": bar_matching["missing_bars"],
                "undetected_pct": bar_matching["undetected_pct"],
                "detail": bar_matching.get("missing_detail") or [],
            },
            "metric6_diameter_accuracy": diameter["qty"],
            "metric7_diameter_steel": diameter["steel"],
            "metric8_overall_steel": steel,
        }

    def _steel(self, est: NormalizedWorkbook, mod: NormalizedWorkbook) -> Dict[str, Any]:
        ekg = est.total_steel_kg
        mkg = mod.total_steel_kg
        diff = mkg - ekg
        diff_pct = _pct(abs(diff), ekg) if ekg else (100.0 if mkg else 0.0)
        return {
            "estimator_total_kg": round(ekg, 3),
            "model_total_kg": round(mkg, 3),
            "difference_kg": round(diff, 3),
            "difference_pct": round(diff_pct, 2),
            "accuracy_pct": round(max(0.0, 100.0 - diff_pct), 2),
            "estimator_total_mt": round(est.total_steel_mt or ekg / 1000.0, 4),
            "model_total_mt": round(mod.total_steel_mt or mkg / 1000.0, 4),
            "difference_mt": round(
                (mod.total_steel_mt or mkg / 1000.0) - (est.total_steel_mt or ekg / 1000.0), 4
            ),
        }

    def _diameter(
        self,
        est: NormalizedWorkbook,
        mod: NormalizedWorkbook,
        bar_matching: Dict[str, Any],
    ) -> Dict[str, Any]:
        est_qty: Dict[int, float] = defaultdict(float)
        mod_qty: Dict[int, float] = defaultdict(float)
        missing_by_dia: Dict[int, int] = defaultdict(int)
        extra_by_dia: Dict[int, int] = defaultdict(int)

        for b in est.beams:
            for bar in b.bars:
                if bar.diameter:
                    est_qty[bar.diameter] += bar.quantity or 1.0
        for b in mod.beams:
            for bar in b.bars:
                if bar.diameter:
                    mod_qty[bar.diameter] += bar.quantity or 1.0

        for row in bar_matching.get("rows") or []:
            d = row.get("diameter") or row.get("model_diameter")
            if not d:
                continue
            d = int(d)
            if row.get("status") == "MISSING":
                missing_by_dia[d] += 1
            elif row.get("status") == "EXTRA":
                # ACCEPTABLE_EXTRA intentionally excluded from Extra % penalty
                extra_by_dia[d] += 1

        all_d = sorted(set(est_qty) | set(mod_qty) | set(est.diameter_kg) | set(mod.diameter_kg))
        qty_rows = []
        steel_rows = []
        for d in all_d:
            eq, mq = est_qty.get(d, 0.0), mod_qty.get(d, 0.0)
            ekg = float(est.diameter_kg.get(d, 0) or 0)
            mkg = float(mod.diameter_kg.get(d, 0) or 0)
            if eq == 0 and mq == 0 and ekg == 0 and mkg == 0:
                continue
            diff_q = mq - eq
            miss = missing_by_dia.get(d, 0)
            extra = extra_by_dia.get(d, 0)
            base = max(1, int(round(eq)) if eq else miss + extra)
            qty_rows.append({
                "diameter": d,
                "diameter_label": f"Y{d}",
                "estimator_quantity": round(eq, 2),
                "model_quantity": round(mq, 2),
                "difference": round(diff_q, 2),
                "difference_pct": _pct(abs(diff_q), eq) if eq else (100.0 if mq else 0.0),
                "missing_pct": _pct(miss, base),
                "extra_pct": _pct(extra, base),
            })
            diff_kg = mkg - ekg
            steel_rows.append({
                "diameter": d,
                "diameter_label": f"Y{d}",
                "estimator_kg": round(ekg, 3),
                "model_kg": round(mkg, 3),
                "difference_kg": round(diff_kg, 3),
                "difference_pct": _pct(abs(diff_kg), ekg) if ekg else (100.0 if mkg else 0.0),
            })
        return {"qty": qty_rows, "steel": steel_rows}
