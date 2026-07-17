"""
phase_vtest32_orchestrator.py — Master orchestrator for Phase V.TEST.3.2.
MODEL_VERSION: 8.1.2

READ-ONLY estimator vs model workbook comparison.
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
from comparison_export import ComparisonExport  # noqa: E402
from comparison_models import ComparisonResult  # noqa: E402
from comparison_reporter import ComparisonReporter  # noqa: E402
from comparison_validator import ComparisonValidator  # noqa: E402
from estimator_workbook_parser import (  # noqa: E402
    EstimatorWorkbookParser,
    discover_estimator_workbook,
)
from model_workbook_parser import ModelWorkbookParser, discover_model_workbook  # noqa: E402

MODEL_VERSION = "8.1.3"
PHASE_ID = "V.TEST.3.2"

_REPO = pathlib.Path(__file__).resolve().parents[3]
_V7 = _REPO / "Version7"
_ESTIMATOR_DIR = _REPO / "Test_Input" / "Third Set Drawings" / "Estimator_Output_3rdSet"


class PhaseVTEST32Orchestrator:

    def __init__(self) -> None:
        self._result = ComparisonResult(
            model_version=MODEL_VERSION,
            phase_id=PHASE_ID,
            timestamp=datetime.now().isoformat(),
            model_workbook=None,  # type: ignore
            estimator_workbook=None,  # type: ignore
        )

    def run(self) -> ComparisonResult:
        print("=" * 72)
        print("Phase V.TEST.3.2 — Benchmark Set 3 Estimator Output Comparison")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print("READ-ONLY — No production code modified")
        print("=" * 72)

        # Discover workbooks
        print("\n[1/5] Discovering workbooks ...")
        est_path = discover_estimator_workbook(_ESTIMATOR_DIR)
        mod_path = discover_model_workbook(_V7)
        if not est_path:
            raise FileNotFoundError(f"No estimator xlsx found in {_ESTIMATOR_DIR}")
        if not mod_path:
            raise FileNotFoundError(
                f"Model workbook not found at Version7/data/output/Production_Output/Estimation_Output.xlsx"
            )
        print(f"  Estimator: {est_path.name}")
        print(f"  Model:     {mod_path.name}")

        # Parse workbooks
        print("\n[2/5] Parsing workbook structures ...")
        est_parser = EstimatorWorkbookParser(est_path)
        mod_parser = ModelWorkbookParser(mod_path)
        try:
            self._result.estimator_workbook = est_parser.workbook_ref()
            self._result.model_workbook = mod_parser.workbook_ref()

            est_summary = est_parser.find_summary_table()
            if not est_summary:
                raise RuntimeError("Reinforcement Total (Pink) table not detected in estimator workbook.")
            mod_summary = mod_parser.parse_project_summary()
            est_blocks = est_parser.parse_beam_blocks()
            mod_beams = mod_parser.parse_beams()

            self._result.estimator_summary = est_summary
            self._result.model_summary = mod_summary

            print(f"  Estimator summary: {est_summary.label} — {est_summary.total_steel_kg:,.2f} kg")
            print(f"  Model summary:     {mod_summary.total_steel_kg:,.2f} kg")
            print(f"  Estimator beams:   {len(est_blocks)}")
            print(f"  Model beams:       {len(mod_beams)}")
        finally:
            est_parser.close()
            mod_parser.close()

        # Compare
        print("\n[3/5] Running engineering comparisons ...")
        self._result.summary_comparison = compare_project_summaries(est_summary, mod_summary)
        self._result.diameter_comparison = compare_diameters(est_summary, mod_summary)
        self._result.role_comparison = compare_roles(est_blocks, mod_beams)
        self._result.beam_coverage = beam_coverage(est_blocks, mod_beams)
        self._result.beam_comparisons = compare_beams(est_blocks, mod_beams)
        self._result.engineering_differences = engineering_differences(
            self._result.beam_comparisons,
            self._result.beam_coverage,
            est_summary,
            mod_summary,
        )
        self._result.root_causes = categorize_root_causes(
            self._result.engineering_differences,
            self._result.beam_coverage,
            mod_summary,
        )
        self._result.accuracy_metrics = accuracy_metrics(
            est_summary,
            mod_summary,
            self._result.diameter_comparison,
            self._result.role_comparison,
            self._result.beam_coverage,
            self._result.beam_comparisons,
        )
        self._result.top_20_differences = top_20_differences(self._result.beam_comparisons)
        self._result.recommended_investigation_order = recommended_investigation_order(
            self._result.root_causes,
            self._result.beam_coverage,
        )

        # Validate
        print("\n[4/5] Validating ...")
        validator = ComparisonValidator()
        self._result.validation = validator.validate(self._result)
        v = self._result.validation
        print(f"  Validation: {v['passed']}/{v['total']} rules passed")

        # Export
        print("\n[5/5] Exporting artefacts ...")
        reporter = ComparisonReporter()
        md = reporter.generate(self._result)
        exporter = ComparisonExport()
        paths = exporter.export_all(self._result, md)
        for name, p in paths.items():
            print(f"  {name}")

        print("\n" + "=" * 72)
        print(f"Overall Estimator Similarity Score: {self._result.accuracy_metrics.get('overall_estimator_similarity_score', 0)}/100")
        print(f"Overall Steel Accuracy: {self._result.accuracy_metrics.get('overall_steel_accuracy_pct', 0):.2f}%")
        print("=" * 72)

        return self._result
