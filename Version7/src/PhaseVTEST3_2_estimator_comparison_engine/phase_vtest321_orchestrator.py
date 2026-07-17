"""
phase_vtest321_orchestrator.py — Phase V.TEST.3.2.1 parser correction orchestrator.
MODEL_VERSION: 8.1.3
"""
from __future__ import annotations

import pathlib
import sys
from datetime import datetime

_SRC = pathlib.Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from comparison_engine import (  # noqa: E402
    accuracy_metrics,
    beam_coverage,
    categorize_root_causes,
    compare_beams,
    compare_diameters,
    compare_project_summaries,
    compare_roles,
    engineering_differences,
    recommended_investigation_order,
    top_20_differences,
)
from comparison_models import ComparisonResult  # noqa: E402
from estimator_workbook_parser import EstimatorWorkbookParser, discover_estimator_workbook  # noqa: E402
from model_workbook_parser import ModelWorkbookParser, discover_model_workbook  # noqa: E402
from parser_correction_export import ParserCorrectionExport  # noqa: E402
from parser_correction_reporter import ParserCorrectionReporter  # noqa: E402
from parser_validator import ParserValidator  # noqa: E402

MODEL_VERSION = "8.1.3"
PHASE_ID = "V.TEST.3.2.1"

_REPO = pathlib.Path(__file__).resolve().parents[3]
_V7 = _REPO / "Version7"
_ESTIMATOR_DIR = _REPO / "Test_Input" / "Third Set Drawings" / "Estimator_Output_3rdSet"

PREVIOUS_INCORRECT_ESTIMATOR_KG = 32092.30


class PhaseVTEST321Orchestrator:

    def run(self) -> ComparisonResult:
        print("=" * 72)
        print("Phase V.TEST.3.2.1 — Estimator Workbook Parser Correction")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print("READ-ONLY — Parser correction only, no production code modified")
        print("=" * 72)

        est_path = discover_estimator_workbook(_ESTIMATOR_DIR)
        mod_path = discover_model_workbook(_V7)
        if not est_path or not mod_path:
            raise FileNotFoundError("Required workbooks not found.")

        print(f"\n  Estimator: {est_path.name}")
        print(f"  Model:     {mod_path.name}")

        est_parser = EstimatorWorkbookParser(est_path)
        mod_parser = ModelWorkbookParser(mod_path)
        try:
            est_summary = est_parser.find_summary_table()
            if not est_summary:
                raise RuntimeError("Pink summary table not detected.")
            mod_summary = mod_parser.parse_project_summary()
            est_blocks = est_parser.parse_beam_blocks()
            mod_beams = mod_parser.parse_beams()
            summary_validation = est_parser.summary_validation
        finally:
            est_parser.close()
            mod_parser.close()

        print(f"\n  Corrected estimator steel: {est_summary.total_steel_kg:,.2f} kg "
              f"(was {PREVIOUS_INCORRECT_ESTIMATOR_KG:,.2f} kg)")
        print(f"  Source: {est_summary.total_steel_source} | Row: {est_summary.source_row}")

        result = ComparisonResult(
            model_version=MODEL_VERSION,
            phase_id=PHASE_ID,
            timestamp=datetime.now().isoformat(),
            model_workbook=None,  # type: ignore
            estimator_workbook=None,  # type: ignore
            estimator_summary=est_summary,
            model_summary=mod_summary,
        )

        result.summary_comparison = compare_project_summaries(est_summary, mod_summary)
        result.diameter_comparison = compare_diameters(est_summary, mod_summary)
        result.role_comparison = compare_roles(est_blocks, mod_beams)
        result.beam_coverage = beam_coverage(est_blocks, mod_beams)
        result.beam_comparisons = compare_beams(est_blocks, mod_beams)
        result.engineering_differences = engineering_differences(
            result.beam_comparisons, result.beam_coverage, est_summary, mod_summary
        )
        result.root_causes = categorize_root_causes(
            result.engineering_differences, result.beam_coverage, mod_summary
        )
        result.accuracy_metrics = accuracy_metrics(
            est_summary, mod_summary, result.diameter_comparison,
            result.role_comparison, result.beam_coverage, result.beam_comparisons,
        )
        result.top_20_differences = top_20_differences(result.beam_comparisons)
        result.recommended_investigation_order = recommended_investigation_order(
            result.root_causes, result.beam_coverage
        )

        parser_validation = ParserValidator().validate(
            est_summary, summary_validation, result.accuracy_metrics, result.summary_comparison
        )
        result.validation = parser_validation

        corrections = {
            "model_version": MODEL_VERSION,
            "phase_id": PHASE_ID,
            "corrections_applied": [
                "Pink ABSTRACT table detected (row 29 headers: TOTAL-MT + kg).",
                "Project steel read from kg column (C14) — never TOTAL-MT×1000 + kg.",
                "Diameter quantities read once from pink MT columns (C6–C12) × 1000.",
                "Detail-section C24 (Steel) no longer used for project total (was 2× error).",
                "Concrete and Shuttering excluded from all accuracy and similarity calculations.",
                "Beam role lines continue to use detail-section kg columns (C17–C24).",
            ],
            "previous_incorrect_estimator_kg": PREVIOUS_INCORRECT_ESTIMATOR_KG,
            "corrected_estimator_kg": est_summary.total_steel_kg,
            "correction_factor": round(
                PREVIOUS_INCORRECT_ESTIMATOR_KG / est_summary.total_steel_kg, 4
            ) if est_summary.total_steel_kg else None,
        }

        md = ParserCorrectionReporter().generate(
            result, summary_validation, parser_validation, corrections,
            previous_steel_kg=PREVIOUS_INCORRECT_ESTIMATOR_KG,
        )
        paths = ParserCorrectionExport().export_all(
            result, summary_validation, parser_validation, corrections, md
        )

        print(f"\n  Parser validation: {parser_validation['passed']}/{parser_validation['total']} rules passed")
        print(f"  Similarity score: {result.accuracy_metrics.get('overall_estimator_similarity_score')}/100")
        print(f"  Steel accuracy:   {result.accuracy_metrics.get('overall_steel_accuracy_pct'):.2f}%")
        print("\n  Exported:")
        for name in paths:
            print(f"    {name}")
        print("=" * 72)

        return result
