"""
Phase QA.1 — Module 12: Benchmark Reporter
Generate comprehensive Engineering Accuracy Report (12 sections).
MODEL_VERSION: 6.5.1
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from benchmark_models import EngineeringBenchmarkResult, MODEL_VERSION


class BenchmarkReporter:
    """Builds structured benchmark reports from validation results."""

    def build_report(
        self,
        result: EngineeringBenchmarkResult,
        error_analysis: Dict[str, Any],
        score_result: Dict[str, Any],
        validator_results: Dict[str, Any],
    ) -> Dict[str, Any]:

        return {
            "report_meta": {
                "model_version": MODEL_VERSION,
                "benchmark_id": result.benchmark_id,
                "drawing_name": result.drawing_name,
                "validation_timestamp": result.validation_timestamp,
                "report_generated_at": datetime.now().isoformat(),
                "benchmark_file": result.benchmark_file,
            },
            "section_1_executive_summary": self._executive_summary(result, score_result),
            "section_2_overall_engineering_score": self._overall_score(result, score_result),
            "section_3_kpi_dashboard": self._kpi_dashboard(result, score_result),
            "section_4_beam_accuracy": self._beam_accuracy_section(validator_results),
            "section_5_reinforcement_accuracy": self._reinforcement_section(validator_results),
            "section_6_geometry_accuracy": self._geometry_section(validator_results),
            "section_7_feature_accuracy": self._feature_section(validator_results),
            "section_8_pattern_accuracy": self._pattern_section(validator_results),
            "section_9_bbs_accuracy": self._bbs_section(validator_results),
            "section_10_steel_weight_accuracy": self._steel_weight_section(validator_results),
            "section_11_error_analysis": self._error_analysis_section(error_analysis),
            "section_12_recommendations": self._recommendations_section(error_analysis, result),
        }

    # ── Section 1: Executive Summary ───────────────────────────────────────
    def _executive_summary(self, result: EngineeringBenchmarkResult, score: Dict) -> Dict:
        return {
            "title": "Engineering Accuracy Benchmark — Executive Summary",
            "drawing": result.drawing_name,
            "model_version": result.model_version,
            "overall_classification": result.classification,
            "weighted_score": result.weighted_score,
            "pass_fail": result.pass_fail,
            "validation_passed": result.validation_passed,
            "key_findings": [
                f"Beam Detection: {result.beam_detection_accuracy}%",
                f"Beam Assignment: {result.beam_assignment_accuracy}%",
                f"Top/Bottom Classification: {result.top_bottom_accuracy}%",
                f"Pattern Recognition: {result.pattern_accuracy}%",
                f"BBS Accuracy: {result.bbs_accuracy}%",
                f"Steel Weight: {'NOT AVAILABLE' if result.steel_weight_accuracy is None else str(result.steel_weight_accuracy) + '%'}",
                f"Overall Engineering Score: {result.weighted_score}/100 ({result.classification})",
            ],
        }

    # ── Section 2: Overall Score ───────────────────────────────────────────
    def _overall_score(self, result: EngineeringBenchmarkResult, score: Dict) -> Dict:
        return {
            "title": "Overall Engineering Score",
            "weighted_score": result.weighted_score,
            "classification": result.classification,
            "pass_fail": result.pass_fail,
            "overall_engineering_accuracy": result.overall_engineering_accuracy,
            "classification_thresholds": {
                "EXCELLENT": "≥ 98.0",
                "VERY_GOOD": "95.0 – 97.99",
                "GOOD":      "90.0 – 94.99",
                "FAIR":      "80.0 – 89.99",
                "POOR":      "< 80.0",
            },
            "kpi_contributions": score.get("kpi_contributions", []),
            "total_weight_applied_pct": score.get("total_weight_applied_pct"),
            "available_kpi_count": score.get("available_kpi_count"),
            "total_kpi_count": score.get("total_kpi_count"),
        }

    # ── Section 3: KPI Dashboard ──────────────────────────────────────────
    def _kpi_dashboard(self, result: EngineeringBenchmarkResult, score: Dict) -> Dict:
        kpis = [
            {"kpi": "KPI 1 — Beam Detection",         "accuracy_pct": result.beam_detection_accuracy,    "target_pct": 100.0},
            {"kpi": "KPI 2 — Beam Assignment",         "accuracy_pct": result.beam_assignment_accuracy,   "target_pct": 95.0},
            {"kpi": "KPI 3 — Geometry",                "accuracy_pct": result.geometry_accuracy,          "target_pct": 95.0},
            {"kpi": "KPI 4 — Feature Extraction",      "accuracy_pct": result.feature_accuracy,           "target_pct": 90.0},
            {"kpi": "KPI 5 — Top/Bottom Classification","accuracy_pct": result.top_bottom_accuracy,        "target_pct": 95.0},
            {"kpi": "KPI 6 — Diameter Recognition",    "accuracy_pct": result.diameter_accuracy,          "target_pct": 98.0},
            {"kpi": "KPI 7 — Quantity Recognition",    "accuracy_pct": result.quantity_accuracy,           "target_pct": 95.0},
            {"kpi": "KPI 8 — Pattern Recognition",     "accuracy_pct": result.pattern_accuracy,           "target_pct": 90.0},
            {"kpi": "KPI 9 — Cut Length",              "accuracy_pct": result.cut_length_accuracy,        "target_pct": 90.0},
            {"kpi": "KPI 10 — Steel Weight",           "accuracy_pct": result.steel_weight_accuracy,      "target_pct": 95.0},
            {"kpi": "KPI 11 — BBS",                    "accuracy_pct": result.bbs_accuracy,               "target_pct": 95.0},
            {"kpi": "KPI 12 — Overall Engineering",    "accuracy_pct": result.overall_engineering_accuracy,"target_pct": 95.0},
        ]
        for kpi in kpis:
            acc = kpi["accuracy_pct"]
            target = kpi["target_pct"]
            if acc is None:
                kpi["status"] = "NOT_AVAILABLE"
                kpi["gap"] = None
            else:
                kpi["gap"] = round(acc - target, 4)
                kpi["status"] = "MET" if acc >= target else "BELOW_TARGET"
        return {"title": "KPI Dashboard", "kpis": kpis}

    # ── Section 4-10: Validator detail sections ───────────────────────────
    def _beam_accuracy_section(self, vr: Dict) -> Dict:
        br = vr.get("beam", {})
        return {
            "title": "Beam Accuracy",
            "expected_count": br.get("expected_count"),
            "detected_count": br.get("detected_count"),
            "matched_count": br.get("matched_count"),
            "missing_beams": br.get("missing_beams", []),
            "false_positive_beams": br.get("false_positive_beams", []),
            "accuracy_pct": br.get("accuracy_pct"),
        }

    def _reinforcement_section(self, vr: Dict) -> Dict:
        rr = vr.get("reinforcement", {})
        return {
            "title": "Reinforcement Accuracy",
            "expected_total_bars": rr.get("total_expected"),
            "detected_total_bars": rr.get("total_detected"),
            "correct_bars": rr.get("total_correct"),
            "missing_bars": rr.get("total_missing"),
            "extra_bars": rr.get("total_extra"),
            "accuracy_pct": rr.get("accuracy_pct"),
            "beam_results": rr.get("beam_results", []),
        }

    def _geometry_section(self, vr: Dict) -> Dict:
        gr = vr.get("geometry", {})
        return {
            "title": "Geometry Accuracy",
            "total_compared": gr.get("total_compared"),
            "within_tolerance": gr.get("within_tolerance"),
            "tolerance_mm": 2.0,
            "mae_mm": gr.get("mae_mm"),
            "rmse_mm": gr.get("rmse_mm"),
            "max_error_mm": gr.get("max_error_mm"),
            "accuracy_pct": gr.get("accuracy_pct"),
        }

    def _feature_section(self, vr: Dict) -> Dict:
        fr = vr.get("feature", {})
        return {
            "title": "Feature Accuracy",
            "feature_coverage": fr.get("feature_coverage"),
            "feature_total": fr.get("feature_total"),
            "overall_accuracy_pct": fr.get("overall_accuracy_pct"),
            "avg_precision": fr.get("avg_precision"),
            "avg_recall": fr.get("avg_recall"),
            "avg_f1": fr.get("avg_f1"),
            "attribute_results": fr.get("attribute_results", {}),
        }

    def _pattern_section(self, vr: Dict) -> Dict:
        pr = vr.get("pattern", {})
        return {
            "title": "Pattern Recognition Accuracy",
            "type_accuracy": pr.get("type_accuracy", {}),
            "span_pattern_accuracy_pct": pr.get("span_pattern_accuracy_pct"),
            "overall_accuracy_pct": pr.get("overall_accuracy_pct"),
            "per_class_accuracy": pr.get("per_class_accuracy", {}),
            "total_correct": pr.get("total_correct"),
            "total_compared": pr.get("total_compared"),
        }

    def _bbs_section(self, vr: Dict) -> Dict:
        br = vr.get("bbs", {})
        return {
            "title": "BBS Accuracy",
            "total_rows": br.get("total_rows"),
            "correct_rows": br.get("correct_rows"),
            "overall_accuracy_pct": br.get("overall_accuracy_pct"),
            "diameter_match_pct": br.get("diameter_match_pct"),
            "quantity_match_pct": br.get("quantity_match_pct"),
            "cut_length_match_pct": br.get("cut_length_match_pct"),
        }

    def _steel_weight_section(self, vr: Dict) -> Dict:
        sr = vr.get("steel_weight", {})
        return {
            "title": "Steel Weight Accuracy",
            "overall_accuracy_pct": sr.get("overall_accuracy_pct"),
            "mae_kg": sr.get("mae_kg"),
            "rmse_kg": sr.get("rmse_kg"),
            "max_error_kg": sr.get("max_error_kg"),
            "beam_comparisons": sr.get("beam_comparisons", []),
            "status": "NOT_AVAILABLE" if sr.get("overall_accuracy_pct") is None else "OK",
        }

    def _error_analysis_section(self, ea: Dict) -> Dict:
        return {
            "title": "Error Analysis",
            "total_error_count": ea.get("total_error_count", 0),
            "type_counts": ea.get("type_counts", {}),
            "severity_counts": ea.get("severity_counts", {}),
            "highest_impact_errors": ea.get("highest_impact_errors", []),
        }

    def _recommendations_section(self, ea: Dict, result: EngineeringBenchmarkResult) -> Dict:
        recs = ea.get("recommendations", [])
        if result.weighted_score >= 98:
            recs.insert(0, "Pipeline meets EXCELLENT standard. Continue monitoring with each new drawing.")
        elif result.weighted_score >= 95:
            recs.insert(0, "Pipeline meets VERY GOOD standard. Minor improvements recommended before Phase L.4.")
        elif result.weighted_score >= 90:
            recs.insert(0, "Pipeline meets GOOD standard. Address identified gaps before production deployment.")
        else:
            recs.insert(0, "Pipeline below GOOD threshold. Engineering review required before Phase L.4.")
        return {
            "title": "Recommendations",
            "recommendations": recs,
            "next_phase_readiness": "READY" if result.weighted_score >= 90 else "NEEDS_IMPROVEMENT",
        }
