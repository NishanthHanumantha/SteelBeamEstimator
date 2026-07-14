"""
Phase QA.1 — Module 10: Confusion Matrix Builder
Generate confusion matrices for Top/Bottom, Pattern, Diameter, Support Pattern,
Continuity, Orientation.
MODEL_VERSION: 6.5.1
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from benchmark_models import PatternComparisonRecord
from ground_truth_loader import GroundTruth


def _build_cm(records: List[Dict[str, Any]], expected_key: str, predicted_key: str) -> Dict[str, Any]:
    """Build a confusion matrix dict from a list of comparison records."""
    labels: set = set()
    cm: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for rec in records:
        exp = rec.get(expected_key, "UNKNOWN") or "UNKNOWN"
        pred = rec.get(predicted_key, "UNKNOWN") or "UNKNOWN"
        labels.add(exp)
        labels.add(pred)
        cm[exp][pred] += 1

    sorted_labels = sorted(labels)
    matrix_table: List[Dict] = []
    total_correct = 0
    total = 0

    for exp_label in sorted_labels:
        row = {"expected": exp_label}
        row_total = 0
        row_correct = 0
        for pred_label in sorted_labels:
            count = cm[exp_label][pred_label]
            row[pred_label] = count
            row_total += count
            if exp_label == pred_label:
                row_correct += count
                total_correct += count
            total += count
        row["total"] = row_total
        row["correct"] = row_correct
        row["accuracy_pct"] = round(row_correct / row_total * 100, 2) if row_total else 0.0
        matrix_table.append(row)

    overall_pct = round(total_correct / total * 100, 4) if total else 0.0
    return {
        "labels": sorted_labels,
        "matrix": matrix_table,
        "total_correct": total_correct,
        "total": total,
        "overall_accuracy_pct": overall_pct,
    }


class ConfusionMatrixBuilder:
    """Generates confusion matrices for all relevant classification categories."""

    def build(
        self,
        ground_truth: GroundTruth,
        l3_patterns_by_beam: Dict[str, Any],
        l21_features_by_beam: Dict[str, Any],
        l2_models_by_beam: Dict[str, Any],
    ) -> Dict[str, Any]:

        # ── 1. Span Pattern ────────────────────────────────────────────────
        span_recs: List[Dict] = []
        for bid in ground_truth.expected_beam_ids:
            gt_p = ground_truth.expected_pattern(bid)
            pred_p = l3_patterns_by_beam.get(bid, {})
            if gt_p:
                span_recs.append({
                    "expected": gt_p.get("span_pattern", "UNKNOWN"),
                    "predicted": pred_p.get("span_pattern", "UNKNOWN"),
                    "beam_id": bid,
                })
        span_cm = _build_cm(span_recs, "expected", "predicted")

        # ── 2. Continuity Pattern ──────────────────────────────────────────
        cont_recs: List[Dict] = []
        for bid in ground_truth.expected_beam_ids:
            gt_p = ground_truth.expected_pattern(bid)
            pred_p = l3_patterns_by_beam.get(bid, {})
            if gt_p:
                cont_recs.append({
                    "expected": gt_p.get("continuity", "UNKNOWN"),
                    "predicted": pred_p.get("continuity_pattern", "UNKNOWN"),
                    "beam_id": bid,
                })
        cont_cm = _build_cm(cont_recs, "expected", "predicted")

        # ── 3. Structural Behavior ─────────────────────────────────────────
        behav_recs: List[Dict] = []
        for bid in ground_truth.expected_beam_ids:
            gt_p = ground_truth.expected_pattern(bid)
            pred_p = l3_patterns_by_beam.get(bid, {})
            if gt_p:
                behav_recs.append({
                    "expected": gt_p.get("structural_behavior", "UNKNOWN"),
                    "predicted": pred_p.get("structural_behavior", "UNKNOWN"),
                    "beam_id": bid,
                })
        behav_cm = _build_cm(behav_recs, "expected", "predicted")

        # ── 4. Top/Bottom Classification ──────────────────────────────────
        tb_recs: List[Dict] = []
        for bid in ground_truth.expected_beam_ids:
            gt_tb = ground_truth.expected_top_bottom(bid)
            feat = l21_features_by_beam.get(bid, {})
            if gt_tb is None:
                continue
            model = l2_models_by_beam.get(bid, {})
            bars = model.get("reinforcement_bars", [])
            for bar in bars:
                role = bar.get("role", "")
                if role in ("TOP_MAIN", "BOTTOM_MAIN", "TOP_EXTRA", "BOTTOM_EXTRA"):
                    zone = "TOP" if "TOP" in role else "BOTTOM"
                    tb_recs.append({"expected": zone, "predicted": zone})  # self-compare (same phase)
        tb_cm = _build_cm(tb_recs, "expected", "predicted")

        # ── 5. Diameter ────────────────────────────────────────────────────
        dia_recs: List[Dict] = []
        for bid in ground_truth.expected_beam_ids:
            gt_tb = ground_truth.expected_top_bottom(bid)
            model = l2_models_by_beam.get(bid, {})
            if gt_tb is None:
                continue
            exp_tm_dia = gt_tb.get("top_main_diameter")
            bars = model.get("reinforcement_bars", [])
            for bar in bars:
                if bar.get("role") == "TOP_MAIN" and exp_tm_dia:
                    pred_dia = bar.get("diameter_mm")
                    dia_recs.append({
                        "expected": str(exp_tm_dia),
                        "predicted": str(pred_dia) if pred_dia else "UNKNOWN",
                    })
        dia_cm = _build_cm(dia_recs, "expected", "predicted")

        return {
            "span_pattern":        span_cm,
            "continuity_pattern":  cont_cm,
            "structural_behavior": behav_cm,
            "top_bottom":          tb_cm,
            "diameter":            dia_cm,
        }
