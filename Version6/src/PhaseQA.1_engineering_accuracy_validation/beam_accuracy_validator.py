"""
Phase QA.1 — Module 2: Beam Accuracy Validator
Compare Expected Beam IDs vs Detected Beam IDs.
MODEL_VERSION: 6.5.1
"""
from __future__ import annotations

from typing import Any, Dict, List

from benchmark_models import BeamAccuracyRecord, KPIRecord, safe_pct
from ground_truth_loader import GroundTruth


class BeamAccuracyValidator:
    """Compares expected vs detected beam IDs and computes Beam Detection KPI."""

    def validate(
        self,
        ground_truth: GroundTruth,
        l2_models_by_beam: Dict[str, Any],
    ) -> Dict[str, Any]:
        expected_ids = set(ground_truth.expected_beam_ids)
        detected_ids = set(l2_models_by_beam.keys())

        matched = expected_ids & detected_ids
        missing = expected_ids - detected_ids
        false_positives = detected_ids - expected_ids

        records: List[BeamAccuracyRecord] = []
        for bid in sorted(expected_ids | detected_ids):
            records.append(BeamAccuracyRecord(
                beam_id=bid,
                expected=bid in expected_ids,
                detected=bid in detected_ids,
                match=bid in matched,
                is_false_positive=bid in false_positives,
            ))

        n_expected = len(expected_ids)
        n_detected = len(detected_ids)
        n_correct = len(matched)
        accuracy = safe_pct(n_correct, n_expected)

        kpi = KPIRecord(
            kpi_name="Beam Detection Accuracy",
            expected=float(n_expected),
            detected=float(n_detected),
            correct=float(n_correct),
            accuracy_pct=accuracy,
            status="OK" if accuracy is not None else "NOT_AVAILABLE",
            notes=f"Missing: {sorted(missing)}  False positives: {sorted(false_positives)}",
        )

        return {
            "kpi": kpi,
            "beam_records": records,
            "expected_count": n_expected,
            "detected_count": n_detected,
            "matched_count": n_correct,
            "missing_beams": sorted(missing),
            "false_positive_beams": sorted(false_positives),
            "accuracy_pct": accuracy,
        }
