"""
bar_matcher.py — Semantic bar matching within matched beams.
MODEL_VERSION: 8.9.1
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from gt_models import BarRecord, BeamRecord

MODEL_VERSION = "8.9.1"

# Role equivalence groups for engineering meaning
_ROLE_EQUIV = {
    "STIRRUP_HOOK": "STIRRUP",
    "STIRRUP": "STIRRUP",
}


def _role_key(role: str) -> str:
    r = (role or "UNKNOWN").upper()
    return _ROLE_EQUIV.get(r, r)


def _qty_close(a: float, b: float) -> bool:
    if a <= 0 and b <= 0:
        return True
    if a <= 0 or b <= 0:
        return False
    return abs(a - b) <= max(0.5, 0.05 * max(a, b))


class BarMatcher:
    """
    Match estimator bars to model bars by role + diameter + quantity.
    Classification: MATCH | MISSING | EXTRA | WRONG_DIAMETER |
                    WRONG_QUANTITY | WRONG_ROLE | PARTIAL_MATCH
    """

    def match_beam_bars(
        self,
        drawing_set: str,
        est_beam: BeamRecord,
        mod_beam: BeamRecord,
    ) -> Dict[str, Any]:
        est_bars = list(est_beam.bars)
        mod_bars = list(mod_beam.bars)
        mod_used = [False] * len(mod_bars)
        results: List[Dict[str, Any]] = []

        for eb in est_bars:
            best_i, best_status, best_score = self._best_match(eb, mod_bars, mod_used)
            if best_i is None:
                results.append(self._row(
                    drawing_set, est_beam.beam_id, eb, None, "MISSING"
                ))
                continue
            mod_used[best_i] = True
            mb = mod_bars[best_i]
            results.append(self._row(
                drawing_set, est_beam.beam_id, eb, mb, best_status
            ))

        for i, mb in enumerate(mod_bars):
            if not mod_used[i]:
                results.append(self._row(
                    drawing_set, est_beam.beam_id, None, mb, "EXTRA"
                ))

        detected = sum(1 for r in results if r["status"] not in ("MISSING", "EXTRA"))
        correct = sum(1 for r in results if r["status"] == "MATCH")
        missing = sum(1 for r in results if r["status"] == "MISSING")
        est_count = len(est_bars)

        return {
            "beam_id": est_beam.beam_id,
            "model_beam_id": mod_beam.beam_id,
            "estimator_bars": est_count,
            "model_bars": len(mod_bars),
            "detected_bars": detected,
            "correct_bars": correct,
            "missing_bars": missing,
            "extra_bars": sum(1 for r in results if r["status"] == "EXTRA"),
            "detection_pct": round(100.0 * detected / est_count, 2) if est_count else 0.0,
            "accuracy_pct": round(100.0 * correct / detected, 2) if detected else 0.0,
            "rows": results,
        }

    def match_all(
        self,
        drawing_set: str,
        pairs: List[Tuple[BeamRecord, BeamRecord]],
        unmatched_est_beams: List[BeamRecord],
    ) -> Dict[str, Any]:
        all_rows: List[Dict[str, Any]] = []
        beam_summaries: List[Dict[str, Any]] = []
        missing_detail: List[Dict[str, Any]] = []

        for eb, mb in pairs:
            bm = self.match_beam_bars(drawing_set, eb, mb)
            beam_summaries.append({k: v for k, v in bm.items() if k != "rows"})
            all_rows.extend(bm["rows"])
            missing_detail.extend([r for r in bm["rows"] if r["status"] == "MISSING"])

        for eb in unmatched_est_beams:
            for bar in eb.bars:
                row = self._row(drawing_set, eb.beam_id, bar, None, "MISSING")
                all_rows.append(row)
                missing_detail.append(row)
            beam_summaries.append({
                "beam_id": eb.beam_id,
                "model_beam_id": None,
                "estimator_bars": len(eb.bars),
                "model_bars": 0,
                "detected_bars": 0,
                "correct_bars": 0,
                "missing_bars": len(eb.bars),
                "extra_bars": 0,
                "detection_pct": 0.0,
                "accuracy_pct": 0.0,
                "status": "BEAM_MISSING",
            })

        est_total = sum(s["estimator_bars"] for s in beam_summaries)
        det_total = sum(s["detected_bars"] for s in beam_summaries)
        cor_total = sum(s["correct_bars"] for s in beam_summaries)
        miss_total = sum(s["missing_bars"] for s in beam_summaries)

        return {
            "model_version": MODEL_VERSION,
            "drawing_set": drawing_set,
            "estimator_bars": est_total,
            "detected_bars": det_total,
            "correct_bars": cor_total,
            "missing_bars": miss_total,
            "detection_pct": round(100.0 * det_total / est_total, 2) if est_total else 0.0,
            "accuracy_pct": round(100.0 * cor_total / det_total, 2) if det_total else 0.0,
            "undetected_pct": round(100.0 * miss_total / est_total, 2) if est_total else 0.0,
            "beam_summaries": beam_summaries,
            "rows": all_rows,
            "missing_detail": missing_detail,
        }

    def _best_match(
        self,
        eb: BarRecord,
        mod_bars: List[BarRecord],
        used: List[bool],
    ) -> Tuple[Optional[int], str, float]:
        best_i: Optional[int] = None
        best_status = "MISSING"
        best_score = -1.0

        er = _role_key(eb.bar_role)
        for i, mb in enumerate(mod_bars):
            if used[i]:
                continue
            mr = _role_key(mb.bar_role)
            role_ok = er == mr
            dia_ok = (
                eb.diameter is None
                or mb.diameter is None
                or eb.diameter == mb.diameter
            )
            qty_ok = _qty_close(eb.quantity, mb.quantity)

            if role_ok and dia_ok and qty_ok:
                score = 3.0
                status = "MATCH"
            elif role_ok and dia_ok and not qty_ok:
                score = 2.0
                status = "WRONG_QUANTITY"
            elif role_ok and not dia_ok and (eb.diameter and mb.diameter):
                score = 1.5
                status = "WRONG_DIAMETER"
            elif not role_ok and dia_ok and qty_ok:
                score = 1.0
                status = "WRONG_ROLE"
            elif role_ok or dia_ok:
                score = 0.5
                status = "PARTIAL_MATCH"
            else:
                continue

            if score > best_score:
                best_score = score
                best_i = i
                best_status = status

        return best_i, best_status, best_score

    @staticmethod
    def _row(
        drawing_set: str,
        beam_id: str,
        est: Optional[BarRecord],
        mod: Optional[BarRecord],
        status: str,
    ) -> Dict[str, Any]:
        return {
            "drawing_set": drawing_set,
            "beam_id": beam_id,
            "bar_role": (est or mod).bar_role if (est or mod) else "",
            "model_role": mod.bar_role if mod else None,
            "diameter": est.diameter if est else (mod.diameter if mod else None),
            "model_diameter": mod.diameter if mod else None,
            "estimator_qty": est.quantity if est else 0.0,
            "model_qty": mod.quantity if mod else 0.0,
            "estimator_steel_kg": est.steel_weight if est else 0.0,
            "model_steel_kg": mod.steel_weight if mod else 0.0,
            "cut_length_est": est.cut_length if est else None,
            "cut_length_model": mod.cut_length if mod else None,
            "status": status,
            "matched": status not in ("MISSING", "EXTRA"),
            "difference_qty": round(
                (mod.quantity if mod else 0.0) - (est.quantity if est else 0.0), 2
            ),
        }
