"""
Phase QA.1 — Module 13: Benchmark Export
Export all 10 benchmark artefacts as JSON files.
MODEL_VERSION: 6.5.1
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
from datetime import datetime
from typing import Any, Dict, List, Optional

from benchmark_models import EngineeringBenchmarkResult, MODEL_VERSION


class BenchmarkExportError(Exception):
    pass


def _serial(obj: Any) -> Any:
    """JSON serializer for dataclasses and other non-serializable types."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    if isinstance(obj, pathlib.Path):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _write_json(path: pathlib.Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, default=_serial, ensure_ascii=False),
        encoding="utf-8",
    )


class BenchmarkExporter:
    """Writes all benchmark artefacts to the output directory."""

    def __init__(self, output_dir: str | pathlib.Path):
        self._out = pathlib.Path(output_dir)

    def export_all(
        self,
        result: EngineeringBenchmarkResult,
        report: Dict[str, Any],
        score_result: Dict[str, Any],
        validator_results: Dict[str, Any],
        confusion_matrices: Dict[str, Any],
        error_analysis: Dict[str, Any],
    ) -> Dict[str, str]:
        """Export all artefacts. Returns dict of filename -> absolute path."""
        ts = datetime.now().isoformat(timespec="seconds").replace(":", "-")
        exported: Dict[str, str] = {}

        # 1. engineering_accuracy_report.json  (full report)
        p = self._out / "engineering_accuracy_report.json"
        _write_json(p, report)
        exported["engineering_accuracy_report"] = str(p)

        # 2. engineering_accuracy_summary.json  (executive summary)
        summary = {
            "model_version": MODEL_VERSION,
            "benchmark_id": result.benchmark_id,
            "drawing_name": result.drawing_name,
            "validation_timestamp": result.validation_timestamp,
            "weighted_score": result.weighted_score,
            "classification": result.classification,
            "pass_fail": result.pass_fail,
            "beam_detection_accuracy": result.beam_detection_accuracy,
            "beam_assignment_accuracy": result.beam_assignment_accuracy,
            "geometry_accuracy": result.geometry_accuracy,
            "feature_accuracy": result.feature_accuracy,
            "top_bottom_accuracy": result.top_bottom_accuracy,
            "pattern_accuracy": result.pattern_accuracy,
            "bbs_accuracy": result.bbs_accuracy,
            "steel_weight_accuracy": result.steel_weight_accuracy,
            "overall_engineering_accuracy": result.overall_engineering_accuracy,
        }
        p = self._out / "engineering_accuracy_summary.json"
        _write_json(p, summary)
        exported["engineering_accuracy_summary"] = str(p)

        # 3. beam_accuracy_report.json
        beam_r = validator_results.get("beam", {})
        beam_report = {
            "model_version": MODEL_VERSION,
            "expected_count": beam_r.get("expected_count"),
            "detected_count": beam_r.get("detected_count"),
            "matched_count": beam_r.get("matched_count"),
            "missing_beams": beam_r.get("missing_beams", []),
            "false_positive_beams": beam_r.get("false_positive_beams", []),
            "accuracy_pct": beam_r.get("accuracy_pct"),
            "beam_records": [dataclasses.asdict(r) for r in beam_r.get("beam_records", [])],
        }
        p = self._out / "beam_accuracy_report.json"
        _write_json(p, beam_report)
        exported["beam_accuracy_report"] = str(p)

        # 4. reinforcement_accuracy_report.json
        rein_r = validator_results.get("reinforcement", {})
        rein_report = {
            "model_version": MODEL_VERSION,
            "total_expected": rein_r.get("total_expected"),
            "total_detected": rein_r.get("total_detected"),
            "total_correct": rein_r.get("total_correct"),
            "total_missing": rein_r.get("total_missing"),
            "total_extra": rein_r.get("total_extra"),
            "accuracy_pct": rein_r.get("accuracy_pct"),
            "beam_results": rein_r.get("beam_results", []),
        }
        p = self._out / "reinforcement_accuracy_report.json"
        _write_json(p, rein_report)
        exported["reinforcement_accuracy_report"] = str(p)

        # 5. pattern_accuracy_report.json
        pat_r = validator_results.get("pattern", {})
        pattern_report = {
            "model_version": MODEL_VERSION,
            "type_accuracy": pat_r.get("type_accuracy", {}),
            "span_pattern_accuracy_pct": pat_r.get("span_pattern_accuracy_pct"),
            "overall_accuracy_pct": pat_r.get("overall_accuracy_pct"),
            "per_class_accuracy": pat_r.get("per_class_accuracy", {}),
            "total_correct": pat_r.get("total_correct"),
            "total_compared": pat_r.get("total_compared"),
            "comparison_records": [dataclasses.asdict(r) for r in pat_r.get("comparison_records", [])],
        }
        p = self._out / "pattern_accuracy_report.json"
        _write_json(p, pattern_report)
        exported["pattern_accuracy_report"] = str(p)

        # 6. bbs_accuracy_report.json
        bbs_r = validator_results.get("bbs", {})
        bbs_report = {
            "model_version": MODEL_VERSION,
            "total_rows": bbs_r.get("total_rows"),
            "correct_rows": bbs_r.get("correct_rows"),
            "overall_accuracy_pct": bbs_r.get("overall_accuracy_pct"),
            "diameter_match_pct": bbs_r.get("diameter_match_pct"),
            "quantity_match_pct": bbs_r.get("quantity_match_pct"),
            "cut_length_match_pct": bbs_r.get("cut_length_match_pct"),
            "bbs_row_records": [dataclasses.asdict(r) for r in bbs_r.get("bbs_row_records", [])],
        }
        p = self._out / "bbs_accuracy_report.json"
        _write_json(p, bbs_report)
        exported["bbs_accuracy_report"] = str(p)

        # 7. steel_weight_accuracy_report.json
        sw_r = validator_results.get("steel_weight", {})
        sw_report = {
            "model_version": MODEL_VERSION,
            "overall_accuracy_pct": sw_r.get("overall_accuracy_pct"),
            "mae_kg": sw_r.get("mae_kg"),
            "rmse_kg": sw_r.get("rmse_kg"),
            "max_error_kg": sw_r.get("max_error_kg"),
            "beam_comparisons": sw_r.get("beam_comparisons", []),
            "status": sw_r.get("kpi", {}).get("status") if hasattr(sw_r.get("kpi", {}), "get") else "UNKNOWN",
        }
        p = self._out / "steel_weight_accuracy_report.json"
        _write_json(p, sw_report)
        exported["steel_weight_accuracy_report"] = str(p)

        # 8. confusion_matrices.json
        p = self._out / "confusion_matrices.json"
        _write_json(p, {"model_version": MODEL_VERSION, "matrices": confusion_matrices})
        exported["confusion_matrices"] = str(p)

        # 9. engineering_score.json
        score_export = {
            "model_version": MODEL_VERSION,
            "benchmark_id": result.benchmark_id,
            "weighted_score": result.weighted_score,
            "classification": result.classification,
            "pass_fail": result.pass_fail,
            "kpi_contributions": score_result.get("kpi_contributions", []),
            "weights_used": score_result.get("weights_used", {}),
            "total_weight_applied_pct": score_result.get("total_weight_applied_pct"),
            "available_kpi_count": score_result.get("available_kpi_count"),
        }
        p = self._out / "engineering_score.json"
        _write_json(p, score_export)
        exported["engineering_score"] = str(p)

        # 10. error_analysis.json
        ea_export = {
            "model_version": MODEL_VERSION,
            "benchmark_id": result.benchmark_id,
            "total_error_count": error_analysis.get("total_error_count", 0),
            "type_counts": error_analysis.get("type_counts", {}),
            "severity_counts": error_analysis.get("severity_counts", {}),
            "recommendations": error_analysis.get("recommendations", []),
            "highest_impact_errors": error_analysis.get("highest_impact_errors", []),
            "all_errors": [dataclasses.asdict(e) for e in error_analysis.get("errors", [])],
        }
        p = self._out / "error_analysis.json"
        _write_json(p, ea_export)
        exported["error_analysis"] = str(p)

        return exported
