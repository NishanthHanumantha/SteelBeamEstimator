"""
Phase QA.1 — Module 8: Steel Weight Accuracy Validator
Compare Expected vs Predicted Steel Weight.
Metrics: Absolute Error, Percentage Error, MAE, RMSE, Max Error.
MODEL_VERSION: 6.5.1
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from benchmark_models import KPIRecord, safe_pct
from ground_truth_loader import GroundTruth


class SteelWeightAccuracyValidator:
    """Validates steel weight against V5 reference (when available)."""

    def validate(
        self,
        ground_truth: GroundTruth,
        v5_steel_weight_data: Optional[Dict[str, Any]],
        l2_models_by_beam: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        if not ground_truth.steel_weight_available:
            kpi = KPIRecord(
                kpi_name="Steel Weight Accuracy",
                expected=None, detected=None, correct=None, accuracy_pct=None,
                status="NOT_AVAILABLE",
                notes="Steel weight reference data not available in V5 (DEFERRED/DEPENDENCY_BLOCKED)",
            )
            return {
                "kpi": kpi,
                "beam_comparisons": [],
                "overall_accuracy_pct": None,
                "mae_kg": None,
                "rmse_kg": None,
                "max_error_kg": None,
            }

        # If steel weight becomes available in future benchmarks
        if v5_steel_weight_data is None:
            kpi = KPIRecord(
                kpi_name="Steel Weight Accuracy",
                expected=None, detected=None, correct=None, accuracy_pct=None,
                status="NOT_AVAILABLE",
                notes="V5 steel weight file not found",
            )
            return {"kpi": kpi, "beam_comparisons": [], "overall_accuracy_pct": None,
                    "mae_kg": None, "rmse_kg": None, "max_error_kg": None}

        results = v5_steel_weight_data.get("results", [])
        computed = [r for r in results if r.get("weight_kg") is not None and r.get("weight_kg") != 0]

        if not computed:
            kpi = KPIRecord(
                kpi_name="Steel Weight Accuracy",
                expected=None, detected=None, correct=None, accuracy_pct=None,
                status="NOT_AVAILABLE",
                notes="All V5 steel weights are DEFERRED",
            )
            return {"kpi": kpi, "beam_comparisons": [], "overall_accuracy_pct": None,
                    "mae_kg": None, "rmse_kg": None, "max_error_kg": None}

        # Group by beam, sum weights
        v5_weight_by_beam: Dict[str, float] = {}
        for r in computed:
            bid = r.get("beam_id", "UNKNOWN")
            v5_weight_by_beam[bid] = v5_weight_by_beam.get(bid, 0.0) + float(r["weight_kg"])

        # Compare against L.2 model weight if available
        comparisons: List[Dict[str, Any]] = []
        errors: List[float] = []

        for bid, v5_w in v5_weight_by_beam.items():
            l2_w = None
            if l2_models_by_beam and bid in l2_models_by_beam:
                l2_w = l2_models_by_beam[bid].get("total_weight_kg")

            abs_err = abs((l2_w or v5_w) - v5_w)
            pct_err = abs_err / v5_w * 100 if v5_w else 0.0

            comparisons.append({
                "beam_id": bid,
                "expected_kg": v5_w,
                "predicted_kg": l2_w,
                "absolute_error_kg": round(abs_err, 4),
                "percentage_error_pct": round(pct_err, 4),
            })
            if l2_w is not None:
                errors.append(abs_err)

        if errors:
            mae = round(sum(errors) / len(errors), 4)
            rmse = round(math.sqrt(sum(e ** 2 for e in errors) / len(errors)), 4)
            max_err = round(max(errors), 4)
            within_5pct = sum(1 for c in comparisons if c["percentage_error_pct"] <= 5.0)
            accuracy = safe_pct(within_5pct, len(comparisons))
        else:
            mae = rmse = max_err = accuracy = None

        kpi = KPIRecord(
            kpi_name="Steel Weight Accuracy",
            expected=float(len(comparisons)),
            detected=float(len(comparisons)),
            correct=float(within_5pct) if errors else None,
            accuracy_pct=accuracy,
            mae=mae,
            rmse=rmse,
            max_error=max_err,
            status="OK" if errors else "PARTIAL",
            notes=f"Compared {len(comparisons)} beams",
        )

        return {
            "kpi": kpi,
            "beam_comparisons": comparisons,
            "overall_accuracy_pct": accuracy,
            "mae_kg": mae,
            "rmse_kg": rmse,
            "max_error_kg": max_err,
        }
