"""Pipeline-wide before/after delta analysis."""

from __future__ import annotations

from typing import Any


def _delta_metric(before: int | float, after: int | float) -> dict[str, Any]:
    return {
        "before": before,
        "after": after,
        "delta": round(after - before, 3) if isinstance(before, float) or isinstance(after, float) else after - before,
    }


class DeltaAnalyzer:
    """Compare PRE-J.1 and POST-J.1 pipeline metrics."""

    METRIC_KEYS = (
        "engineering_objects",
        "normalized_bars",
        "calculated_bars",
        "beam_schedule_rows",
        "excel_rows",
        "steel_weight_kg",
        "inventory_coverage_percent",
        "bbs_rows",
        "specifications",
        "calculation_contexts",
    )

    def analyze(self, baseline_snapshot: dict[str, Any]) -> dict[str, Any]:
        pre = baseline_snapshot.get("pre_j1") or {}
        post = baseline_snapshot.get("post_j1") or {}
        metrics: dict[str, Any] = {}
        for key in self.METRIC_KEYS:
            metrics[key] = _delta_metric(pre.get(key, 0), post.get(key, 0))

        return {
            "phase": baseline_snapshot.get("phase"),
            "model_version": baseline_snapshot.get("model_version"),
            "baseline_method": baseline_snapshot.get("baseline_method"),
            "pipeline_delta": metrics,
            "summary": {
                "engineering_objects": metrics["engineering_objects"],
                "normalized_bars": metrics["normalized_bars"],
                "calculated_bars": metrics["calculated_bars"],
                "beam_schedule_rows": metrics["beam_schedule_rows"],
                "excel_rows": metrics["excel_rows"],
                "steel_weight_kg": metrics["steel_weight_kg"],
                "inventory_coverage_percent": metrics["inventory_coverage_percent"],
            },
        }
