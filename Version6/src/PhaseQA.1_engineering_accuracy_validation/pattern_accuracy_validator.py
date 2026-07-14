"""
Phase QA.1 — Module 6: Pattern Accuracy Validator
Compare Expected vs Predicted patterns from Phase L.3.
Produces Confusion Matrix + Per-class Accuracy.
MODEL_VERSION: 6.5.1
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from benchmark_models import KPIRecord, PatternComparisonRecord, safe_pct
from ground_truth_loader import GroundTruth


class PatternAccuracyValidator:
    """Validates L.3 engineering patterns against ground truth."""

    def validate(
        self,
        ground_truth: GroundTruth,
        l3_patterns_by_beam: Dict[str, Any],
    ) -> Dict[str, Any]:

        records: List[PatternComparisonRecord] = []
        confusion: Dict[str, Dict[str, Dict[str, int]]] = {
            "span_pattern":        defaultdict(lambda: defaultdict(int)),
            "continuity_pattern":  defaultdict(lambda: defaultdict(int)),
            "structural_behavior": defaultdict(lambda: defaultdict(int)),
        }

        for beam_id in ground_truth.expected_beam_ids:
            gt_pattern = ground_truth.expected_pattern(beam_id)
            if gt_pattern is None:
                continue

            pred = l3_patterns_by_beam.get(beam_id, {})

            for ptype, gt_key, pred_key in [
                ("span_pattern",        "span_pattern",  "span_pattern"),
                ("continuity_pattern",  "continuity",    "continuity_pattern"),
                ("structural_behavior", "structural_behavior", "structural_behavior"),
            ]:
                expected_val = gt_pattern.get(gt_key, "UNKNOWN")
                predicted_val = pred.get(pred_key, "UNKNOWN") if pred else "UNKNOWN"
                match = (expected_val == predicted_val)

                records.append(PatternComparisonRecord(
                    beam_id=beam_id,
                    pattern_type=ptype,
                    expected=expected_val,
                    predicted=predicted_val,
                    match=match,
                ))
                confusion[ptype][expected_val][predicted_val] += 1

        # Per-type accuracy
        type_accuracy: Dict[str, float] = {}
        total_correct = 0
        total_compared = 0

        for ptype in ["span_pattern", "continuity_pattern", "structural_behavior"]:
            type_records = [r for r in records if r.pattern_type == ptype]
            if not type_records:
                continue
            correct = sum(1 for r in type_records if r.match)
            type_accuracy[ptype] = round(correct / len(type_records) * 100, 4)
            total_correct += correct
            total_compared += len(type_records)

        # Per-class accuracy for span_pattern
        per_class: Dict[str, Dict] = {}
        for cls_val, row in confusion["span_pattern"].items():
            tp = row.get(cls_val, 0)
            total_cls = sum(row.values())
            per_class[cls_val] = {
                "tp": tp, "total": total_cls,
                "accuracy_pct": round(tp / total_cls * 100, 2) if total_cls else 0.0,
            }

        overall_accuracy = safe_pct(total_correct, total_compared)
        span_accuracy = type_accuracy.get("span_pattern")

        kpi = KPIRecord(
            kpi_name="Pattern Recognition Accuracy",
            expected=float(total_compared),
            detected=float(total_compared),
            correct=float(total_correct),
            accuracy_pct=span_accuracy,   # primary metric = span_pattern accuracy
            status="OK" if total_compared > 0 else "NOT_AVAILABLE",
            notes=f"Span: {type_accuracy.get('span_pattern')}%  "
                  f"Continuity: {type_accuracy.get('continuity_pattern')}%  "
                  f"Behaviour: {type_accuracy.get('structural_behavior')}%",
        )

        return {
            "kpi": kpi,
            "comparison_records": records,
            "confusion_matrices": {k: dict(v) for k, v in confusion.items()},
            "type_accuracy": type_accuracy,
            "per_class_accuracy": per_class,
            "total_correct": total_correct,
            "total_compared": total_compared,
            "overall_accuracy_pct": overall_accuracy,
            "span_pattern_accuracy_pct": span_accuracy,
        }
