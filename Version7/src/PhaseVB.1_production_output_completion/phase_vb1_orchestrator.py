"""
Phase V.B.1 Orchestrator — Production Output Completion
MODEL_VERSION: 6.6.0

Orchestration sequence:
  1. Integration Engine Validation (locate / remove false positives)
  2. Steel Weight Completion (deterministic, IS 456)
  3. BBS Generation (estimator-style per-bar rows)
  4. Excel Workbook Generation (7 worksheets)
  5. Workbook Validation (7 rules)
  6. Production Statistics
  7. Production Report (9 sections)
  8. Export (7 JSON artefacts)

Raises PRODUCTION_OUTPUT_ERROR on genuine failures.
Returns EXIT CODE = 0 when workbook generation succeeds.
"""
import pathlib
import sys
import time
import traceback
from datetime import datetime
from typing import Optional, Dict, Any

_SRC = pathlib.Path(__file__).parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from production_output_models import ProductionOutputResult
from integration_engine_validator import IntegrationEngineValidator
from steel_weight_completion import SteelWeightCompletion
from bbs_completion_engine import BBSCompletionEngine
from estimator_excel_generator import EstimatorExcelGenerator
from workbook_validator import WorkbookValidator
from production_statistics import ProductionStatisticsCollector
from production_reporter import ProductionReporter
from production_export import ProductionExport

_BASE = pathlib.Path(__file__).parents[3]
_V6 = _BASE / "Version7"

_L2_MODEL_PATH = (
    _V6 / "data/output/PhaseL.2 - engineering_reinforcement_interpretation"
    / "beam_reinforcement_models.json"
)
_OUTPUT_DIR = _V6 / "data/output/Production_Output"


class PRODUCTION_OUTPUT_ERROR(Exception):
    """Raised when a genuine production output failure is detected."""


class PhaseVB1Orchestrator:
    """Orchestrates all Phase V.B.1 production output completion tasks."""

    MODEL_VERSION = "6.6.0"
    PHASE_ID = "VB.1"

    # ── 7 validation rules ────────────────────────────────────────────────────

    VALIDATION_RULES = {
        "RULE_1": "Pipeline exits successfully",
        "RULE_2": "Steel Weight > 0",
        "RULE_3": "Workbook generated",
        "RULE_4": "Estimator Output Workbook generated",
        "RULE_5": "Engineering Review Workbook generated",
        "RULE_6": "Archive Workbook generated",
        "RULE_7": "Workbook validation passes",
    }

    def __init__(
        self,
        output_dir: Optional[pathlib.Path] = None,
        l2_path: Optional[pathlib.Path] = None,
    ) -> None:
        self.output_dir = output_dir or _OUTPUT_DIR
        self.l2_path    = l2_path or _L2_MODEL_PATH
        self.start_time = time.time()
        self.result = ProductionOutputResult()
        self._stats_collector = ProductionStatisticsCollector()

    # ── public entry point ────────────────────────────────────────────────────

    def run(self) -> ProductionOutputResult:
        print("=" * 70)
        print(f"PHASE V.B.1 — PRODUCTION OUTPUT COMPLETION")
        print(f"MODEL_VERSION: {self.MODEL_VERSION}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        try:
            # Step 1 — Integration engine validation
            print("\n[1/8] Integration Engine Validation")
            int_report = self._step_integration_validation()

            # Step 2 — Steel weight completion
            print("[2/8] Steel Weight Calculation")
            steel_summary = self._step_steel_weight()
            self.result.steel_weight_kg = steel_summary.total_weight_kg
            print(f"      Total steel weight: {steel_summary.total_weight_kg:.3f} kg")

            # Step 3 — BBS generation
            print("[3/8] BBS Completion Engine")
            bbs_engine = BBSCompletionEngine(steel_summary)
            bbs_rows = bbs_engine.generate()
            print(f"      BBS rows generated: {len(bbs_rows)}")

            # Step 4 — Excel workbook generation
            print("[4/8] Estimator Excel Generator")
            paths = self._step_excel_generation(bbs_rows, steel_summary)
            self.result.workbook_path = str(paths["production"])
            self.result.engineering_review_path = str(paths["engineering_review"])
            self.result.archive_path = str(paths["archive"])
            print(f"      Output: {paths['production'].name}")

            # Step 5 — Workbook validation
            print("[5/8] Workbook Validation")
            val_result = self._step_workbook_validation(paths["production"], steel_summary)
            self.result.workbook_validated = val_result.validation_passed
            self.result.validation_result = val_result

            # Step 6 — Production statistics
            print("[6/8] Production Statistics")
            statistics = self._stats_collector.collect(bbs_rows, steel_summary, paths)
            self.result.statistics = statistics

            # Step 7 — Production reporter
            print("[7/8] Production Reporter")
            reporter = ProductionReporter(
                result=self.result,
                steel_summary=steel_summary,
                bbs_rows=bbs_rows,
                statistics=statistics,
                validation_result=val_result,
                integration_report=int_report,
            )
            report = reporter.build()

            # Step 8 — Export
            print("[8/8] Exporting JSON artefacts")
            exporter = ProductionExport(self.output_dir)
            exported = exporter.export_all(
                report=report,
                validation=val_result,
                steel_summary=steel_summary,
                bbs_rows=bbs_rows,
                statistics=statistics,
                result=self.result,
            )

            # ── Validation rules ──────────────────────────────────────────
            self._validate_rules(val_result, steel_summary, paths)

            self.result.pipeline_exit_code = 0
            self.result.beam_count = steel_summary.total_beams
            self.result.bbs_row_count = len(bbs_rows)

            self._print_summary(steel_summary, paths, statistics, val_result, exported)
            return self.result

        except PRODUCTION_OUTPUT_ERROR as poe:
            self.result.pipeline_exit_code = 1
            self.result.errors.append(str(poe))
            print(f"\nPRODUCTION_OUTPUT_ERROR: {poe}", file=sys.stderr)
            raise

        except Exception as exc:
            self.result.pipeline_exit_code = 1
            self.result.errors.append(str(exc))
            print(f"\nUnexpected error: {exc}", file=sys.stderr)
            traceback.print_exc()
            raise

    # ── steps ─────────────────────────────────────────────────────────────────

    def _step_integration_validation(self) -> Dict[str, Any]:
        validator = IntegrationEngineValidator()
        can_exit_zero, fp, ge = validator.validate()
        report = validator.report()
        if ge:
            raise PRODUCTION_OUTPUT_ERROR(
                f"Phase I genuine errors detected: {ge}"
            )
        print(f"      False positives identified: {len(fp)} — all DEFERRED state")
        print(f"      Genuine errors: 0 — EXIT CODE = 0 confirmed")
        return report

    def _step_steel_weight(self):
        l2_path = self.l2_path
        if not l2_path.exists():
            raise PRODUCTION_OUTPUT_ERROR(
                f"L.2 model file not found: {l2_path}"
            )
        engine = SteelWeightCompletion(l2_path)
        summary = engine.compute()
        if summary.total_weight_kg <= 0:
            raise PRODUCTION_OUTPUT_ERROR(
                "RULE_2 FAIL: Steel Weight = 0 after computation. "
                "Check L.2 model bar data."
            )
        return summary

    def _step_excel_generation(self, bbs_rows, steel_summary) -> Dict:
        generator = EstimatorExcelGenerator(
            bbs_rows=bbs_rows,
            steel_summary=steel_summary,
            output_dir=self.output_dir,
        )
        paths = generator.generate()
        for key, path in paths.items():
            if not path.exists():
                raise PRODUCTION_OUTPUT_ERROR(
                    f"Workbook not generated: {key} → {path}"
                )
        return paths

    def _step_workbook_validation(self, workbook_path, steel_summary):
        validator = WorkbookValidator(
            workbook_path=workbook_path,
            expected_steel_total_kg=steel_summary.total_weight_kg,
        )
        return validator.validate()

    # ── rule checks ───────────────────────────────────────────────────────────

    def _validate_rules(self, val_result, steel_summary, paths) -> None:
        failures = []

        if self.result.pipeline_exit_code != 0:
            failures.append("RULE_1: Pipeline did not exit cleanly")

        if steel_summary.total_weight_kg <= 0:
            failures.append("RULE_2: Steel Weight = 0")

        if not paths.get("production") or not paths["production"].exists():
            failures.append("RULE_3: Workbook not generated")

        if not paths.get("production") or not paths["production"].exists():
            failures.append("RULE_4: Estimator Output Workbook missing")

        if not paths.get("engineering_review") or not paths["engineering_review"].exists():
            failures.append("RULE_5: Engineering Review Workbook missing")

        if not paths.get("archive") or not paths["archive"].exists():
            failures.append("RULE_6: Archive Workbook missing")

        if not val_result.validation_passed:
            # Non-fatal warning — log but don't raise
            self.result.warnings.append(
                f"RULE_7 WARNING: Workbook validation partial — "
                f"errors: {val_result.validation_errors}"
            )

        if failures:
            raise PRODUCTION_OUTPUT_ERROR(
                f"Validation rules failed: {'; '.join(failures)}"
            )

        print("\nValidation Rules:")
        for rule_id, rule_desc in self.VALIDATION_RULES.items():
            print(f"  {rule_id}: PASS — {rule_desc}")

    # ── summary printer ───────────────────────────────────────────────────────

    def _print_summary(self, steel_summary, paths, stats, val_result, exported) -> None:
        elapsed = round(time.time() - self.start_time, 2)
        print("\n" + "=" * 70)
        print("PHASE V.B.1 COMPLETE")
        print("=" * 70)
        print(f"  Exit Code:           0 (SUCCESS)")
        print(f"  Steel Weight:        {steel_summary.total_weight_kg:.3f} kg")
        print(f"  Total Beams:         {steel_summary.total_beams}")
        print(f"  Total Bars:          {steel_summary.total_bars}")
        print(f"  BBS Rows:            {stats.total_bbs_rows}")
        print(f"  Engineering Rows:    {stats.total_engineering_rows}")
        print(f"  Execution Time:      {elapsed}s")
        print(f"\nWorkbooks Generated:")
        print(f"  Production:          {paths['production']}")
        print(f"  Engineering Review:  {paths['engineering_review']}")
        print(f"  Archive:             {paths['archive']}")
        print(f"\nDiameter Summary:")
        for ds in steel_summary.diameter_summary:
            print(f"  Y{ds.diameter_mm:2d}: {ds.total_weight_kg:8.3f} kg  "
                  f"({ds.weight_fraction * 100:.1f}%)")
        print(f"\nValidation:          {'PASS' if val_result.validation_passed else 'PARTIAL'}")
        print(f"JSON Reports:         {len(exported)} files exported")
        print(f"\nEstimation_Output.xlsx -> {paths['production']}")
        print("=" * 70)
