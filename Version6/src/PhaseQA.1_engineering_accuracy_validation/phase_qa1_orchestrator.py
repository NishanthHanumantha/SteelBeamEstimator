"""
Phase QA.1 — Engineering Accuracy Benchmark & Validation Framework
phase_qa1_orchestrator.py  — Main pipeline orchestrator.
MODEL_VERSION: 6.5.1

Pipeline:
  Load Ground Truth
    → Load Model Outputs
    → Beam Validation
    → Geometry Validation
    → Reinforcement Validation
    → Feature Validation
    → Pattern Validation
    → BBS Validation
    → Steel Weight Validation
    → Engineering Score
    → Confusion Matrix
    → Error Analysis
    → Report
    → Export
"""
from __future__ import annotations

import pathlib
from datetime import datetime
from typing import Any, Dict, List, Optional

from beam_accuracy_validator import BeamAccuracyValidator
from benchmark_export import BenchmarkExporter
from benchmark_loader import ModelOutputLoader
from benchmark_models import (
    DEFAULT_WEIGHTS,
    EngineeringBenchmarkResult,
    KPIRecord,
    MODEL_VERSION,
    classify_score,
    safe_pct,
)
from benchmark_reporter import BenchmarkReporter
from bbs_accuracy_validator import BBSAccuracyValidator
from confusion_matrix_builder import ConfusionMatrixBuilder
from engineering_score_calculator import EngineeringScoreCalculator
from error_analyzer import ErrorAnalyzer
from feature_accuracy_validator import FeatureAccuracyValidator
from geometry_accuracy_validator import GeometryAccuracyValidator
from ground_truth_loader import GroundTruth, GroundTruthLoader
from pattern_accuracy_validator import PatternAccuracyValidator
from reinforcement_accuracy_validator import ReinforcementAccuracyValidator
from steel_weight_accuracy_validator import SteelWeightAccuracyValidator


# ── Validation Rules ────────────────────────────────────────────────────────
class BenchmarkValidationError(Exception):
    pass


def _validate_rules(
    ground_truth: GroundTruth,
    validator_results: Dict[str, Any],
    score_result: Dict[str, Any],
) -> Dict[str, bool]:
    rules: Dict[str, bool] = {}

    # RULE_1: Ground Truth Exists
    rules["RULE_1_GROUND_TRUTH_EXISTS"] = bool(ground_truth.expected_beam_ids)

    # RULE_2: All Beams Compared
    beam_r = validator_results.get("beam", {})
    rules["RULE_2_ALL_BEAMS_COMPARED"] = (
        beam_r.get("expected_count", 0) > 0
        and beam_r.get("matched_count", 0) >= 0
    )

    # RULE_3: All Bars Compared
    rein_r = validator_results.get("reinforcement", {})
    rules["RULE_3_ALL_BARS_COMPARED"] = rein_r.get("total_expected", 0) > 0

    # RULE_4: Every KPI Calculated
    kpi_keys = ["beam", "geometry", "reinforcement", "feature", "pattern", "bbs"]
    rules["RULE_4_EVERY_KPI_CALCULATED"] = all(k in validator_results for k in kpi_keys)

    # RULE_5: Overall Score Produced
    rules["RULE_5_OVERALL_SCORE_PRODUCED"] = score_result.get("weighted_score") is not None

    failed = [k for k, v in rules.items() if not v]
    if failed:
        raise BenchmarkValidationError(
            f"BENCHMARK_VALIDATION_ERROR — Failed rules: {failed}"
        )

    return rules


class PhaseQA1Orchestrator:
    """Orchestrates the full Phase QA.1 benchmark pipeline."""

    def __init__(
        self,
        ground_truth_path: str | pathlib.Path,
        output_dir: Optional[str | pathlib.Path] = None,
        weights: Optional[Dict[str, float]] = None,
    ):
        self._gt_path = pathlib.Path(ground_truth_path)
        self._output_dir = pathlib.Path(output_dir) if output_dir else self._default_output_dir()
        self._weights = weights or DEFAULT_WEIGHTS

    def _default_output_dir(self) -> pathlib.Path:
        here = pathlib.Path(__file__).resolve()
        return here.parents[2] / "data" / "output" / "PhaseQA.1_engineering_accuracy_validation"

    def run(self) -> EngineeringBenchmarkResult:
        print("[QA.1] Loading ground truth …")
        gt_loader = GroundTruthLoader()
        ground_truth = gt_loader.load(self._gt_path)

        print("[QA.1] Loading model outputs (read-only) …")
        loader = ModelOutputLoader()
        l2_by_beam   = loader.get_l2_models_by_beam()
        l3_by_beam   = loader.get_l3_patterns_by_beam()
        l21_by_beam  = loader.get_l21_features_by_beam()
        v5_bbs_list  = loader.get_v5_bbs_list()
        v5_cuts      = loader.get_v5_cut_lengths_computed()
        v5_sw        = loader.load_v5_steel_weight()
        l22_extended = loader.load_l22_extended_models()
        l22_by_beam  = ({m["beam_id"]: m for m in l22_extended.get("models", []) if "beam_id" in m}
                        if l22_extended else None)
        v5_bar_id    = loader.load_v5_bar_identity()
        v5_bar_id_list = (v5_bar_id.get("results", []) if v5_bar_id else [])

        validator_results: Dict[str, Any] = {}

        # ── MODULE 2: Beam Accuracy ────────────────────────────────────────
        print("[QA.1] Module 2 — Beam Accuracy Validation …")
        beam_val = BeamAccuracyValidator()
        beam_result = beam_val.validate(ground_truth, l2_by_beam)
        validator_results["beam"] = beam_result

        # ── MODULE 3: Reinforcement Accuracy ──────────────────────────────
        print("[QA.1] Module 3 — Reinforcement Accuracy Validation …")
        rein_val = ReinforcementAccuracyValidator()
        rein_result = rein_val.validate(ground_truth, l2_by_beam, l22_by_beam)
        validator_results["reinforcement"] = rein_result

        # ── MODULE 4: Geometry Accuracy ───────────────────────────────────
        print("[QA.1] Module 4 — Geometry Accuracy Validation …")
        geom_val = GeometryAccuracyValidator()
        geom_result = geom_val.validate(ground_truth, l2_by_beam)
        validator_results["geometry"] = geom_result

        # ── MODULE 5: Feature Accuracy ────────────────────────────────────
        print("[QA.1] Module 5 — Feature Accuracy Validation …")
        feat_val = FeatureAccuracyValidator()
        feat_result = feat_val.validate(ground_truth, l21_by_beam, l2_by_beam)
        validator_results["feature"] = feat_result

        # ── MODULE 6: Pattern Accuracy ────────────────────────────────────
        print("[QA.1] Module 6 — Pattern Accuracy Validation …")
        pat_val = PatternAccuracyValidator()
        pat_result = pat_val.validate(ground_truth, l3_by_beam)
        validator_results["pattern"] = pat_result

        # ── MODULE 7: BBS Accuracy ────────────────────────────────────────
        print("[QA.1] Module 7 — BBS Accuracy Validation …")
        bbs_val = BBSAccuracyValidator()
        bbs_result = bbs_val.validate(ground_truth, v5_bbs_list, l2_by_beam, v5_bar_id_list)
        validator_results["bbs"] = bbs_result

        # ── MODULE 8: Steel Weight Accuracy ───────────────────────────────
        print("[QA.1] Module 8 — Steel Weight Accuracy Validation …")
        sw_val = SteelWeightAccuracyValidator()
        sw_result = sw_val.validate(ground_truth, v5_sw, l2_by_beam)
        validator_results["steel_weight"] = sw_result

        # ── Compute extra KPIs (top/bottom, diameter, quantity) ───────────
        tb_accuracy = self._compute_top_bottom_accuracy(ground_truth, l2_by_beam, l21_by_beam)
        dia_accuracy = self._compute_diameter_accuracy(ground_truth, l2_by_beam)
        qty_accuracy = self._compute_quantity_accuracy(ground_truth, l2_by_beam)
        cut_accuracy = self._compute_cut_length_accuracy(ground_truth, v5_cuts, l2_by_beam)

        extra_kpi_records: List[KPIRecord] = [
            KPIRecord("Top/Bottom Classification Accuracy", None, None,
                      None, tb_accuracy, status="OK" if tb_accuracy else "NOT_AVAILABLE"),
            KPIRecord("Diameter Recognition Accuracy", None, None,
                      None, dia_accuracy, status="OK" if dia_accuracy else "NOT_AVAILABLE"),
            KPIRecord("Quantity Recognition Accuracy", None, None,
                      None, qty_accuracy, status="OK" if qty_accuracy else "NOT_AVAILABLE"),
            KPIRecord("Cut Length Accuracy", None, None,
                      None, cut_accuracy, status="OK" if cut_accuracy else "NOT_AVAILABLE"),
        ]

        # Combine all KPI records
        all_kpi_records: List[KPIRecord] = [
            beam_result["kpi"],
            rein_result["kpi"],
            geom_result["kpi"],
            feat_result["kpi"],
            pat_result["kpi"],
            bbs_result["kpi"],
            sw_result["kpi"],
            *extra_kpi_records,
        ]

        # ── MODULE 9: Engineering Score ────────────────────────────────────
        print("[QA.1] Module 9 — Engineering Score Calculation …")
        calc = EngineeringScoreCalculator(self._weights)
        score_result = calc.compute(all_kpi_records)

        # ── MODULE 10: Confusion Matrices ─────────────────────────────────
        print("[QA.1] Module 10 — Confusion Matrix Generation …")
        cm_builder = ConfusionMatrixBuilder()
        confusion_matrices = cm_builder.build(ground_truth, l3_by_beam, l21_by_beam, l2_by_beam)

        # ── Validation Rules ──────────────────────────────────────────────
        print("[QA.1] Validating benchmark rules …")
        try:
            rule_results = _validate_rules(ground_truth, validator_results, score_result)
            validation_passed = True
        except BenchmarkValidationError as exc:
            print(f"[QA.1] WARNING: {exc}")
            rule_results = {}
            validation_passed = False

        # ── Build EngineeringBenchmarkResult ─────────────────────────────
        ws = score_result["weighted_score"]
        result = EngineeringBenchmarkResult(
            benchmark_id=ground_truth.benchmark_id,
            drawing_name=ground_truth.drawing_name,
            model_version=MODEL_VERSION,
            validation_timestamp=datetime.now().isoformat(),

            beam_detection_accuracy=beam_result.get("accuracy_pct"),
            beam_assignment_accuracy=rein_result.get("accuracy_pct"),
            geometry_accuracy=geom_result.get("accuracy_pct"),
            feature_accuracy=feat_result.get("overall_accuracy_pct"),
            top_bottom_accuracy=tb_accuracy,
            diameter_accuracy=dia_accuracy,
            quantity_accuracy=qty_accuracy,
            pattern_accuracy=pat_result.get("span_pattern_accuracy_pct"),
            cut_length_accuracy=cut_accuracy,
            steel_weight_accuracy=sw_result.get("overall_accuracy_pct"),
            bbs_accuracy=bbs_result.get("overall_accuracy_pct"),
            overall_engineering_accuracy=score_result.get("overall_engineering_accuracy"),

            weighted_score=ws,
            classification=classify_score(ws),
            pass_fail=score_result.get("pass_fail", "FAIL"),

            kpi_records=all_kpi_records,
            beam_accuracy_records=beam_result.get("beam_records", []),
            geometry_error_records=geom_result.get("error_records", []),
            pattern_comparison_records=pat_result.get("comparison_records", []),
            bbs_row_records=bbs_result.get("bbs_row_records", []),

            rule_results=rule_results,
            validation_passed=validation_passed,
            confusion_matrices=confusion_matrices,
            benchmark_file=str(self._gt_path),
        )

        # ── MODULE 11: Error Analysis ──────────────────────────────────────
        print("[QA.1] Module 11 — Error Analysis …")
        err_analyzer = ErrorAnalyzer()
        error_analysis = err_analyzer.analyze(
            beam_result, rein_result, geom_result, feat_result,
            pat_result, bbs_result, sw_result,
        )
        result.error_summary = error_analysis.get("errors", [])

        # ── MODULE 12: Report ──────────────────────────────────────────────
        print("[QA.1] Module 12 — Benchmark Report Generation …")
        reporter = BenchmarkReporter()
        report = reporter.build_report(result, error_analysis, score_result, validator_results)

        # ── MODULE 13: Export ──────────────────────────────────────────────
        print("[QA.1] Module 13 — Exporting artefacts …")
        exporter = BenchmarkExporter(self._output_dir)
        exported = exporter.export_all(
            result, report, score_result, validator_results,
            confusion_matrices, error_analysis,
        )

        print(f"\n[QA.1] ========== BENCHMARK COMPLETE ==========")
        print(f"[QA.1] Drawing         : {result.drawing_name}")
        print(f"[QA.1] Model Version   : {result.model_version}")
        print(f"[QA.1] Weighted Score  : {result.weighted_score:.2f}/100")
        print(f"[QA.1] Classification  : {result.classification}")
        print(f"[QA.1] Pass/Fail       : {result.pass_fail}")
        print(f"[QA.1] Validation      : {'PASSED' if result.validation_passed else 'FAILED'}")
        print(f"[QA.1] Artefacts       : {len(exported)} files exported")
        print(f"[QA.1] Output dir      : {self._output_dir}")
        print("[QA.1] ===========================================\n")

        return result

    # ── Extra KPI helpers ──────────────────────────────────────────────────
    def _get_bars_for_role(self, model: Dict[str, Any], role: str) -> List[Dict[str, Any]]:
        """Extract bar entries for a given role from role-specific lists."""
        role_to_field = {
            "TOP_MAIN":    "top_main_bars",
            "BOTTOM_MAIN": "bottom_main_bars",
            "TOP_EXTRA":   "top_extra_bars",
            "BOTTOM_EXTRA":"bottom_extra_bars",
            "STIRRUP":     "stirrups",
            "SIDE_FACE_REINFORCEMENT": "side_face_reinforcement",
        }
        field = role_to_field.get(role)
        if not field:
            return []
        lst = model.get(field, [])
        return lst if isinstance(lst, list) else []

    def _compute_top_bottom_accuracy(
        self,
        gt: GroundTruth,
        l2_by_beam: Dict[str, Any],
        l21_by_beam: Dict[str, Any],
    ) -> Optional[float]:
        correct = 0
        total = 0
        for bid in gt.expected_beam_ids:
            gt_tb = gt.expected_top_bottom(bid)
            if gt_tb is None:
                continue
            if gt.expected_bars_for_beam(bid) and gt.expected_bars_for_beam(bid).get("recovered"):
                continue  # skip recovered beams
            model = l2_by_beam.get(bid, {})
            exp_tm_dia = gt_tb.get("top_main_diameter")
            exp_bm_dia = gt_tb.get("bottom_main_diameter")
            for bar in self._get_bars_for_role(model, "TOP_MAIN"):
                if exp_tm_dia is not None:
                    total += 1
                    dia = bar.get("diameter_mm")
                    if dia and abs(float(dia) - float(exp_tm_dia)) < 1:
                        correct += 1
            for bar in self._get_bars_for_role(model, "BOTTOM_MAIN"):
                if exp_bm_dia is not None:
                    total += 1
                    dia = bar.get("diameter_mm")
                    if dia and abs(float(dia) - float(exp_bm_dia)) < 1:
                        correct += 1
        return safe_pct(correct, total)

    def _compute_diameter_accuracy(
        self,
        gt: GroundTruth,
        l2_by_beam: Dict[str, Any],
    ) -> Optional[float]:
        correct = 0
        total = 0
        for bid in gt.expected_beam_ids:
            gt_tb = gt.expected_top_bottom(bid)
            if gt_tb is None:
                continue
            if gt.expected_bars_for_beam(bid) and gt.expected_bars_for_beam(bid).get("recovered"):
                continue
            model = l2_by_beam.get(bid, {})
            for role, exp_key in [("TOP_MAIN", "top_main_diameter"), ("BOTTOM_MAIN", "bottom_main_diameter")]:
                expected_dia = gt_tb.get(exp_key)
                if expected_dia is None:
                    continue
                for bar in self._get_bars_for_role(model, role):
                    dia = bar.get("diameter_mm")
                    total += 1
                    if dia and abs(float(dia) - float(expected_dia)) < 1:
                        correct += 1
        return safe_pct(correct, total)

    def _compute_quantity_accuracy(
        self,
        gt: GroundTruth,
        l2_by_beam: Dict[str, Any],
    ) -> Optional[float]:
        correct = 0
        total = 0
        for bid in gt.expected_beam_ids:
            gt_entry = gt.expected_bars_for_beam(bid)
            if gt_entry is None:
                continue
            if gt_entry.get("recovered"):
                continue  # skip recovered beams
            model = l2_by_beam.get(bid, {})
            by_role = model.get("bar_count_by_role", {})
            # If bar_count_by_role is all zeros, count from role-specific lists
            if not any(v > 0 for v in by_role.values()):
                by_role = {}
                for role, field in [("TOP_MAIN","top_main_bars"),("BOTTOM_MAIN","bottom_main_bars"),
                                     ("TOP_EXTRA","top_extra_bars"),("BOTTOM_EXTRA","bottom_extra_bars"),
                                     ("STIRRUP","stirrups"),("SIDE_FACE_REINFORCEMENT","side_face_reinforcement")]:
                    lst = model.get(field, [])
                    by_role[role] = len(lst) if isinstance(lst, list) else 0
            for role in ["TOP_MAIN", "BOTTOM_MAIN", "TOP_EXTRA", "BOTTOM_EXTRA", "STIRRUP"]:
                exp = gt_entry.get(role)
                if exp is None:
                    continue
                total += 1
                det = by_role.get(role, 0)
                if int(exp) == int(det):
                    correct += 1
        return safe_pct(correct, total)

    def _compute_cut_length_accuracy(
        self,
        gt: GroundTruth,
        v5_cuts: List[Dict[str, Any]],
        l2_by_beam: Dict[str, Any],
    ) -> Optional[float]:
        """
        Cut length is computed in the BBS pipeline (Phase I), not in Phase L.2.
        Phase L.2 model bars do not carry cut_length_mm.
        Return None (NOT_AVAILABLE) — this KPI will be evaluated when Phase I
        is re-implemented in V6.
        """
        return None
