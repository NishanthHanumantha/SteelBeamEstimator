"""
Phase QA.1 — Module 4: Geometry Accuracy Validator
Compare Beam Length, Depth, Width vs ground truth with ±2 mm tolerance.
Metrics: MAE, RMSE, Max Error.
MODEL_VERSION: 6.5.1
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from benchmark_models import GeometryErrorRecord, KPIRecord, safe_pct
from ground_truth_loader import GroundTruth


class GeometryAccuracyValidator:
    """Validates beam geometry against ground truth within tolerance."""

    def validate(
        self,
        ground_truth: GroundTruth,
        l2_models_by_beam: Dict[str, Any],
    ) -> Dict[str, Any]:
        tolerance = ground_truth.geometry_tolerance_mm
        errors: List[GeometryErrorRecord] = []
        within_tol = 0
        total_compared = 0

        for beam_id in ground_truth.expected_beam_ids:
            model = l2_models_by_beam.get(beam_id)
            if model is None:
                continue
            geom = model.get("geometry") or model.get("beam_geometry") or {}

            fields = {
                "span_mm":  (
                    ground_truth.expected_span_mm(beam_id),
                    geom.get("clear_span_mm") or geom.get("span_mm"),
                ),
                "depth_mm": (
                    ground_truth.expected_depth_mm(beam_id),
                    geom.get("depth_mm") or geom.get("beam_depth_mm"),
                ),
                "width_mm": (
                    ground_truth.expected_width_mm(beam_id),
                    geom.get("width_mm") or geom.get("beam_width_mm"),
                ),
            }

            for field, (exp_val, pred_val) in fields.items():
                if exp_val is None or pred_val is None:
                    continue
                try:
                    exp_f = float(exp_val)
                    pred_f = float(pred_val)
                except (TypeError, ValueError):
                    continue

                abs_err = abs(pred_f - exp_f)
                ok = abs_err <= tolerance
                errors.append(GeometryErrorRecord(
                    beam_id=beam_id,
                    field=field,
                    expected_value=exp_f,
                    predicted_value=pred_f,
                    absolute_error_mm=round(abs_err, 3),
                    within_tolerance=ok,
                    tolerance_mm=tolerance,
                ))
                total_compared += 1
                if ok:
                    within_tol += 1

        # Compute MAE, RMSE, Max Error
        if errors:
            errs = [e.absolute_error_mm for e in errors]
            mae = round(sum(errs) / len(errs), 3)
            rmse = round(math.sqrt(sum(e ** 2 for e in errs) / len(errs)), 3)
            max_err = round(max(errs), 3)
        else:
            mae = rmse = max_err = 0.0

        accuracy = safe_pct(within_tol, total_compared)

        kpi = KPIRecord(
            kpi_name="Geometry Accuracy",
            expected=float(total_compared),
            detected=float(total_compared),
            correct=float(within_tol),
            accuracy_pct=accuracy,
            mae=mae,
            rmse=rmse,
            max_error=max_err,
            status="OK" if total_compared > 0 else "NOT_AVAILABLE",
            notes=f"Tolerance: ±{tolerance} mm  Fields compared: {total_compared}",
        )

        return {
            "kpi": kpi,
            "error_records": errors,
            "total_compared": total_compared,
            "within_tolerance": within_tol,
            "mae_mm": mae,
            "rmse_mm": rmse,
            "max_error_mm": max_err,
            "accuracy_pct": accuracy,
        }
