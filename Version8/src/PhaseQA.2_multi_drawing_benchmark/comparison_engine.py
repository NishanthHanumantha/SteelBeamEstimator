"""
comparison_engine.py — Compare Estimator Excel vs Model Excel (all 8 metrics).
MODEL_VERSION: 8.9.0
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

MODEL_VERSION = "8.9.0"

# IS 1786 unit weights kg/m (for quantity fallback if needed)
_UNIT_WT = {8: 0.395, 10: 0.617, 12: 0.888, 16: 1.58, 20: 2.47, 25: 3.85, 32: 6.31}

DIAMETERS = (8, 10, 12, 16, 20, 25, 32)


def _norm_beam(bid: str) -> str:
    return str(bid or "").strip().upper().replace(" ", "")


def _role_family(role: str) -> str:
    r = (role or "").upper().strip()
    if r.startswith("TOP_EXTRA") or "TOP EXTRA" in r:
        return "TOP_EXTRA"
    if r.startswith("TOP") or "TOP MAIN" in r:
        return "TOP_MAIN"
    if r.startswith("BOTTOM_EXTRA") or "BOTTOM EXTRA" in r:
        return "BOTTOM_EXTRA"
    if r.startswith("BOTTOM") or "BOTTOM MAIN" in r:
        return "BOTTOM_MAIN"
    if "HOOK" in r:
        return "STIRRUP_HOOK"
    if "STIRRUP" in r:
        return "STIRRUP"
    if "SPACER" in r:
        return "SPACER_BAR"
    if "SIDE" in r or r in ("SFR", "SIDE_FACE_REINFORCEMENT"):
        return "SIDE_FACE_REINFORCEMENT"
    if "DEVELOPMENT" in r or "LAP" in r or "ANCHOR" in r:
        return r.split()[0] if r else "UNKNOWN"
    return r or "UNKNOWN"


def _dia_key(d: Any) -> Optional[int]:
    if d is None:
        return None
    try:
        v = int(round(float(d)))
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def _pct(num: float, den: float) -> float:
    if den <= 0:
        return 0.0
    return round(100.0 * num / den, 2)


def _bar_key(role: str, diameter: Optional[int]) -> Tuple[str, Optional[int]]:
    return (_role_family(role), diameter)


class ComparisonEngine:
    """
    Excel-vs-Excel comparison.
    Estimator workbook = ground truth.
    Model workbook     = pipeline output.
    """

    def compare(
        self,
        drawing_set: str,
        estimator: Any,
        model: Any,
    ) -> Dict[str, Any]:
        est_beams = {_norm_beam(b.beam_id): b for b in (estimator.beams or [])}
        mod_beams = {_norm_beam(b.beam_id): b for b in (model.beams or []) if _norm_beam(b.beam_id)}

        beam_report = self._metric_beams(drawing_set, est_beams, mod_beams)
        bar_report = self._metric_bars(drawing_set, est_beams, mod_beams)
        diameter_report = self._metric_diameters(estimator, model, est_beams, mod_beams)
        steel_report = self._metric_steel(estimator, model)
        errors = self._classify_errors(beam_report, bar_report, diameter_report, steel_report)

        return {
            "model_version": MODEL_VERSION,
            "drawing_set": drawing_set,
            "beam_detection": beam_report["detection"],
            "beam_identification": beam_report["identification"],
            "beam_rows": beam_report["rows"],
            "beam_level": bar_report.get("beam_level") or [],
            "bar_detection": bar_report["detection"],
            "bar_accuracy": bar_report["accuracy"],
            "bar_rows": bar_report["rows"],
            "missing_bars": bar_report["missing"],
            "diameter_comparison": diameter_report["comparison"],
            "diameter_steel": diameter_report["steel"],
            "steel_quantity": steel_report,
            "errors": errors,
            "summary": self._drawing_summary(
                drawing_set, beam_report, bar_report, diameter_report, steel_report, errors
            ),
        }

    # ── Metrics 1–2: beams ────────────────────────────────────────────────────

    def _metric_beams(
        self,
        drawing_set: str,
        est_beams: Dict[str, Any],
        mod_beams: Dict[str, Any],
    ) -> Dict[str, Any]:
        est_ids = set(est_beams)
        mod_ids = set(mod_beams)
        matched = sorted(est_ids & mod_ids)
        missing = sorted(est_ids - mod_ids)
        extra = sorted(mod_ids - est_ids)

        total = len(est_ids)
        detected = len(matched)  # beams present in both = detected & matched IDs
        # Spec: Detection % = Detected / Total Estimator Beams
        # Spec: Correct ID among detected — for Excel-vs-Excel, ID match IS detection
        detection_pct = _pct(detected, total)
        id_accuracy_pct = _pct(len(matched), detected) if detected else 0.0

        rows = []
        for bid in sorted(est_ids | mod_ids):
            in_est = bid in est_ids
            in_mod = bid in mod_ids
            status = "MATCHED" if (in_est and in_mod) else (
                "MISSING" if in_est else "EXTRA"
            )
            rows.append({
                "drawing_set": drawing_set,
                "beam_id": bid,
                "detected": in_mod and in_est,
                "matched": in_mod and in_est,
                "in_estimator": in_est,
                "in_model": in_mod,
                "status": status,
            })

        return {
            "detection": {
                "total_estimator_beams": total,
                "detected_beams": detected,
                "undetected_beams": len(missing),
                "extra_beams": len(extra),
                "detection_pct": detection_pct,
                "missing_ids": missing,
                "extra_ids": extra,
                "matched_ids": matched,
            },
            "identification": {
                "correctly_matched": len(matched),
                "incorrect_ids": 0,  # Excel uses same ID space; extras counted separately
                "accuracy_pct": id_accuracy_pct,
            },
            "rows": rows,
        }

    # ── Metrics 3–5: bars ─────────────────────────────────────────────────────

    def _collect_bars(self, beam) -> List[Dict[str, Any]]:
        bars = []
        for row in beam.reinforcement_rows or []:
            role = _role_family(getattr(row, "role", "") or getattr(row, "description", ""))
            dia = _dia_key(getattr(row, "diameter", None) or getattr(row, "diameter_column", None))
            # Prefer diameter from diameter_kg keys if diameter missing
            if dia is None and getattr(row, "diameter_kg", None):
                nonzero = [int(k) for k, v in row.diameter_kg.items() if float(v or 0) > 0]
                if len(nonzero) == 1:
                    dia = nonzero[0]
            qty = getattr(row, "number_of_bars", None)
            try:
                qty_f = float(qty) if qty is not None else 0.0
            except (TypeError, ValueError):
                qty_f = 0.0
            steel = float(getattr(row, "steel", 0.0) or 0.0)
            bars.append({
                "role": role,
                "diameter": dia,
                "quantity": qty_f,
                "steel_kg": steel,
                "description": getattr(row, "description", "") or "",
                "key": _bar_key(role, dia),
            })
        return bars

    def _metric_bars(
        self,
        drawing_set: str,
        est_beams: Dict[str, Any],
        mod_beams: Dict[str, Any],
    ) -> Dict[str, Any]:
        bar_rows: List[Dict[str, Any]] = []
        missing_rows: List[Dict[str, Any]] = []
        beam_level: List[Dict[str, Any]] = []

        total_est = total_det = total_correct = total_missing = 0

        for bid in sorted(set(est_beams) | set(mod_beams)):
            est_bars = self._collect_bars(est_beams[bid]) if bid in est_beams else []
            mod_bars = self._collect_bars(mod_beams[bid]) if bid in mod_beams else []

            # Multiset match by (role, diameter)
            mod_pool = Counter(b["key"] for b in mod_bars)
            used_mod: Counter = Counter()

            beam_correct = beam_detected = beam_missing = 0
            beam_est = len(est_bars)

            for eb in est_bars:
                key = eb["key"]
                available = mod_pool[key] - used_mod[key]
                if available > 0:
                    used_mod[key] += 1
                    beam_detected += 1
                    # Quantity check among matched role+diameter
                    mb = next(
                        (m for m in mod_bars
                         if m["key"] == key
                         and used_mod[key] <= sum(1 for x in mod_bars if x["key"] == key)),
                        None,
                    )
                    # Find a model bar with same key not yet consumed for qty compare
                    qty_ok = True
                    dia_ok = True
                    role_ok = True
                    matched_mod = None
                    for m in mod_bars:
                        if m["key"] == key and m.get("_used") is not True:
                            m["_used"] = True
                            matched_mod = m
                            break
                    if matched_mod:
                        if eb["quantity"] and matched_mod["quantity"]:
                            qty_ok = abs(eb["quantity"] - matched_mod["quantity"]) <= max(
                                0.5, 0.05 * eb["quantity"]
                            )
                        correct = role_ok and dia_ok and qty_ok
                        if correct:
                            beam_correct += 1
                        status = "CORRECT" if correct else (
                            "WRONG_QUANTITY" if not qty_ok else "MISCLASSIFIED"
                        )
                        bar_rows.append({
                            "drawing_set": drawing_set,
                            "beam_id": bid,
                            "bar_role": eb["role"],
                            "diameter": eb["diameter"],
                            "estimator_qty": eb["quantity"],
                            "model_qty": matched_mod["quantity"] if matched_mod else 0,
                            "matched": True,
                            "difference": round(
                                (matched_mod["quantity"] if matched_mod else 0) - eb["quantity"], 2
                            ),
                            "status": status,
                        })
                    else:
                        beam_correct += 1
                        bar_rows.append({
                            "drawing_set": drawing_set,
                            "beam_id": bid,
                            "bar_role": eb["role"],
                            "diameter": eb["diameter"],
                            "estimator_qty": eb["quantity"],
                            "model_qty": eb["quantity"],
                            "matched": True,
                            "difference": 0,
                            "status": "CORRECT",
                        })
                else:
                    beam_missing += 1
                    missing_rows.append({
                        "drawing_set": drawing_set,
                        "beam_id": bid,
                        "bar_role": eb["role"],
                        "diameter": eb["diameter"],
                        "estimator_qty": eb["quantity"],
                        "model_qty": 0,
                        "matched": False,
                        "difference": -eb["quantity"],
                        "status": "MISSING",
                    })
                    bar_rows.append({
                        "drawing_set": drawing_set,
                        "beam_id": bid,
                        "bar_role": eb["role"],
                        "diameter": eb["diameter"],
                        "estimator_qty": eb["quantity"],
                        "model_qty": 0,
                        "matched": False,
                        "difference": -eb["quantity"],
                        "status": "MISSING",
                    })

            # Extra model bars
            for mb in mod_bars:
                if mb.get("_used"):
                    continue
                bar_rows.append({
                    "drawing_set": drawing_set,
                    "beam_id": bid,
                    "bar_role": mb["role"],
                    "diameter": mb["diameter"],
                    "estimator_qty": 0,
                    "model_qty": mb["quantity"],
                    "matched": False,
                    "difference": mb["quantity"],
                    "status": "EXTRA",
                })

            det_pct = _pct(beam_detected, beam_est)
            acc_pct = _pct(beam_correct, beam_detected) if beam_detected else 0.0
            est_steel = float(getattr(est_beams.get(bid), "total_steel_kg", 0) or 0) if bid in est_beams else 0.0
            mod_steel = float(getattr(mod_beams.get(bid), "total_steel_kg", 0) or 0) if bid in mod_beams else 0.0

            beam_level.append({
                "drawing_set": drawing_set,
                "beam_id": bid,
                "detected": bid in est_beams and bid in mod_beams,
                "matched": bid in est_beams and bid in mod_beams,
                "estimator_bars": beam_est,
                "detected_bars": beam_detected,
                "correct_bars": beam_correct,
                "missing_bars": beam_missing,
                "detection_pct": det_pct,
                "accuracy_pct": acc_pct,
                "steel_difference_kg": round(mod_steel - est_steel, 3),
                "status": (
                    "PASS" if beam_missing == 0 and beam_correct == beam_detected and bid in mod_beams
                    else ("MISSING_BEAM" if bid not in mod_beams else "FAIL")
                ),
            })

            total_est += beam_est
            total_det += beam_detected
            total_correct += beam_correct
            total_missing += beam_missing

        return {
            "detection": {
                "estimator_bars": total_est,
                "detected_bars": total_det,
                "detection_pct": _pct(total_det, total_est),
            },
            "accuracy": {
                "correct_bars": total_correct,
                "incorrect_bars": max(0, total_det - total_correct),
                "accuracy_pct": _pct(total_correct, total_det) if total_det else 0.0,
                "undetected_bars": total_missing,
                "undetected_pct": _pct(total_missing, total_est),
            },
            "rows": bar_rows,
            "missing": missing_rows,
            "beam_level": beam_level,
        }

    # ── Metrics 6–7: diameter ─────────────────────────────────────────────────

    def _metric_diameters(
        self,
        estimator: Any,
        model: Any,
        est_beams: Dict[str, Any],
        mod_beams: Dict[str, Any],
    ) -> Dict[str, Any]:
        def _dia_kg(beams: Dict[str, Any]) -> Dict[int, float]:
            out: Dict[int, float] = defaultdict(float)
            for b in beams.values():
                for k, v in (getattr(b, "diameter_kg", None) or {}).items():
                    try:
                        out[int(k)] += float(v or 0)
                    except (TypeError, ValueError):
                        pass
            return dict(out)

        est_kg = _dia_kg(est_beams)
        mod_kg = _dia_kg(mod_beams)

        # Prefer summary table diameters when beam breakup is empty
        est_sum = getattr(estimator.steel_summary, "diameter_summary", {}) or {}
        mod_sum = getattr(model.steel_summary, "diameter_summary", {}) or {}
        # diameter_summary is often in MT — convert to kg if totals look small
        def _as_kg(summary: dict, fallback: Dict[int, float]) -> Dict[int, float]:
            if fallback and sum(fallback.values()) > 0:
                return fallback
            result: Dict[int, float] = {}
            for k, v in summary.items():
                try:
                    dia = int(k)
                    val = float(v or 0)
                    # Heuristic: if value < 50 treat as MT
                    result[dia] = val * 1000.0 if val < 50 else val
                except (TypeError, ValueError):
                    pass
            return result

        est_kg = _as_kg(est_sum, est_kg)
        mod_kg = _as_kg(mod_sum, mod_kg)

        # Count correct/incorrect bar detections per diameter
        est_count: Counter = Counter()
        mod_count: Counter = Counter()
        for b in est_beams.values():
            for row in b.reinforcement_rows or []:
                d = _dia_key(getattr(row, "diameter", None))
                if d:
                    est_count[d] += 1
        for b in mod_beams.values():
            for row in b.reinforcement_rows or []:
                d = _dia_key(getattr(row, "diameter", None))
                if d:
                    mod_count[d] += 1

        all_dias = sorted(set(est_kg) | set(mod_kg) | set(est_count) | set(mod_count) | set(DIAMETERS))
        comparison = []
        steel_rows = []
        for d in all_dias:
            e = float(est_kg.get(d, 0) or 0)
            m = float(mod_kg.get(d, 0) or 0)
            if e == 0 and m == 0 and est_count[d] == 0 and mod_count[d] == 0:
                continue
            diff = m - e
            diff_pct = _pct(abs(diff), e) if e else (100.0 if m else 0.0)
            correct = min(est_count[d], mod_count[d])
            incorrect = abs(est_count[d] - mod_count[d])
            comparison.append({
                "diameter": d,
                "diameter_label": f"Y{d}",
                "estimator_qty_bars": est_count[d],
                "model_qty_bars": mod_count[d],
                "difference_bars": mod_count[d] - est_count[d],
                "difference_pct_bars": _pct(abs(mod_count[d] - est_count[d]), est_count[d]) if est_count[d] else 0.0,
                "correct_detection": correct,
                "incorrect_detection": incorrect,
            })
            steel_rows.append({
                "diameter": d,
                "diameter_label": f"Y{d}",
                "estimator_kg": round(e, 3),
                "model_kg": round(m, 3),
                "difference_kg": round(diff, 3),
                "difference_pct": round(diff_pct, 2),
                "absolute_error_kg": round(abs(diff), 3),
                "correct_count": correct,
                "incorrect_count": incorrect,
            })

        return {"comparison": comparison, "steel": steel_rows}

    # ── Metric 8: overall steel ───────────────────────────────────────────────

    def _metric_steel(self, estimator: Any, model: Any) -> Dict[str, Any]:
        est_kg = float(getattr(estimator.steel_summary, "total_kg", 0) or 0)
        mod_kg = float(getattr(model.steel_summary, "total_kg", 0) or 0)
        # Fallback: sum beam steels
        if est_kg <= 0:
            est_kg = sum(float(getattr(b, "total_steel_kg", 0) or 0) for b in estimator.beams)
        if mod_kg <= 0:
            mod_kg = sum(float(getattr(b, "total_steel_kg", 0) or 0) for b in model.beams)
        # MT from summary if present
        est_mt = float(getattr(estimator.steel_summary, "total_mt", 0) or 0) or est_kg / 1000.0
        mod_mt = float(getattr(model.steel_summary, "total_mt", 0) or 0) or mod_kg / 1000.0
        diff = mod_kg - est_kg
        diff_pct = _pct(abs(diff), est_kg) if est_kg else (100.0 if mod_kg else 0.0)
        accuracy = max(0.0, 100.0 - diff_pct)
        return {
            "estimator_total_kg": round(est_kg, 3),
            "model_total_kg": round(mod_kg, 3),
            "difference_kg": round(diff, 3),
            "difference_pct": round(diff_pct, 2),
            "accuracy_pct": round(accuracy, 2),
            "estimator_total_mt": round(est_mt, 4),
            "model_total_mt": round(mod_mt, 4),
            "difference_mt": round(mod_mt - est_mt, 4),
        }

    # ── Error classification ──────────────────────────────────────────────────

    def _classify_errors(
        self,
        beam_report: Dict[str, Any],
        bar_report: Dict[str, Any],
        diameter_report: Dict[str, Any],
        steel_report: Dict[str, Any],
    ) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = []
        for bid in beam_report["detection"].get("missing_ids") or []:
            items.append({"error_type": "Beam Missing", "beam_id": bid, "detail": f"Beam {bid} absent in model"})
        for bid in beam_report["detection"].get("extra_ids") or []:
            items.append({"error_type": "Beam Mismatch", "beam_id": bid, "detail": f"Extra model beam {bid}"})
        for row in bar_report.get("missing") or []:
            items.append({
                "error_type": "Bar Missing",
                "beam_id": row.get("beam_id"),
                "detail": f"{row.get('bar_role')} Y{row.get('diameter')} qty={row.get('estimator_qty')}",
            })
        for row in bar_report.get("rows") or []:
            st = row.get("status")
            if st == "WRONG_QUANTITY":
                items.append({
                    "error_type": "Wrong Quantity",
                    "beam_id": row.get("beam_id"),
                    "detail": f"{row.get('bar_role')} est={row.get('estimator_qty')} model={row.get('model_qty')}",
                })
            elif st == "MISCLASSIFIED":
                items.append({
                    "error_type": "Bar Misclassification",
                    "beam_id": row.get("beam_id"),
                    "detail": f"{row.get('bar_role')} Y{row.get('diameter')}",
                })
        for drow in diameter_report.get("steel") or []:
            if float(drow.get("difference_pct") or 0) > 5.0 and float(drow.get("estimator_kg") or 0) > 0:
                items.append({
                    "error_type": "Wrong Diameter",
                    "beam_id": f"Y{drow.get('diameter')}",
                    "detail": f"Steel error {drow.get('difference_pct')}%",
                })
        if float(steel_report.get("difference_pct") or 0) > 2.0:
            items.append({
                "error_type": "Wrong Steel Weight",
                "beam_id": "PROJECT",
                "detail": (
                    f"est={steel_report.get('estimator_total_kg')} kg "
                    f"model={steel_report.get('model_total_kg')} kg "
                    f"({steel_report.get('difference_pct')}%)"
                ),
            })

        freq: Counter = Counter(i["error_type"] for i in items)
        return {
            "items": items,
            "frequency": dict(sorted(freq.items(), key=lambda x: -x[1])),
            "total_errors": len(items),
        }

    def _drawing_summary(
        self,
        drawing_set: str,
        beam_report: Dict[str, Any],
        bar_report: Dict[str, Any],
        diameter_report: Dict[str, Any],
        steel_report: Dict[str, Any],
        errors: Dict[str, Any],
    ) -> Dict[str, Any]:
        det = beam_report["detection"]
        bid = beam_report["identification"]
        bdet = bar_report["detection"]
        bacc = bar_report["accuracy"]
        return {
            "drawing_set": drawing_set,
            "beam_detection_pct": det["detection_pct"],
            "beam_accuracy_pct": bid["accuracy_pct"],
            "bar_detection_pct": bdet["detection_pct"],
            "bar_accuracy_pct": bacc["accuracy_pct"],
            "steel_accuracy_pct": steel_report["accuracy_pct"],
            "total_estimator_beams": det["total_estimator_beams"],
            "detected_beams": det["detected_beams"],
            "estimator_bars": bdet["estimator_bars"],
            "detected_bars": bdet["detected_bars"],
            "correct_bars": bacc["correct_bars"],
            "missing_bars": bacc["undetected_bars"],
            "estimator_kg": steel_report["estimator_total_kg"],
            "model_kg": steel_report["model_total_kg"],
            "error_count": errors["total_errors"],
            "top_errors": list(errors["frequency"].items())[:5],
        }
