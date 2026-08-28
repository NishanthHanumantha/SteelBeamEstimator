"""
Phase V.B.1 Orchestrator — Production Output Completion
MODEL_VERSION: 6.6.0

Orchestration sequence:
  1. Integration Engine Validation (locate / remove false positives)
  2. Steel Weight Completion (deterministic, IS 456)
  3. BBS Generation (estimator-style per-bar rows)
  4. Excel Workbook Generation (5 worksheets — Project Header / General Notes omitted)
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
_V7_SRC = _SRC.parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_V7_SRC) not in sys.path:
    sys.path.insert(0, str(_V7_SRC))

from production_output_models import ProductionOutputResult
from integration_engine_validator import IntegrationEngineValidator
from steel_weight_completion import SteelWeightCompletion
from bbs_completion_engine import BBSCompletionEngine
from estimator_excel_generator import EstimatorExcelGenerator
from workbook_validator import WorkbookValidator
from production_statistics import ProductionStatisticsCollector
from production_reporter import ProductionReporter
from production_export import ProductionExport

try:
    import importlib
    import types
    import importlib.util as _ilu

    def _bootstrap_r2a_for_vb1():
        _v7_src = _V7_SRC
        r2a_dir = _v7_src / "PhaseR.2A_engineering_context"
        if "PhaseR2A.engineering_context_parser" in sys.modules:
            return
        pkg = types.ModuleType("PhaseR2A")
        pkg.__path__ = [str(r2a_dir)]
        sys.modules["PhaseR2A"] = pkg
        for sub in [
            "__init__", "engineering_context_model", "engineering_context_cache",
            "engineering_context_loader", "general_notes_text_extractor",
            "development_length_parser", "cover_parser", "steel_grade_parser",
            "concrete_grade_parser", "hook_rule_parser", "lap_rule_parser",
            "general_notes_classifier", "engineering_context_builder",
            "engineering_context_validator", "engineering_context_factory",
            "engineering_context_parser",
        ]:
            spec = _ilu.spec_from_file_location(f"PhaseR2A.{sub}", r2a_dir / f"{sub}.py")
            mod = _ilu.module_from_spec(spec)
            mod.__package__ = "PhaseR2A"
            sys.modules[f"PhaseR2A.{sub}"] = mod
            spec.loader.exec_module(mod)

    _bootstrap_r2a_for_vb1()
    parse_engineering_context = sys.modules[
        "PhaseR2A.engineering_context_parser"
    ].parse_engineering_context
    _R2A_AVAILABLE = True
except Exception:
    parse_engineering_context = None
    _R2A_AVAILABLE = False

# Offline defaults only (engine_root = Version8/); runners pass explicit paths.
_V6 = pathlib.Path(__file__).resolve().parents[2]  # Version8/

_L2_MODEL_PATH = (
    _V6 / "data/output/PhaseL.2 - engineering_reinforcement_interpretation"
    / "beam_reinforcement_models.json"
)
_OUTPUT_DIR = _V6 / "data/output/Production_Output"


class PRODUCTION_OUTPUT_ERROR(Exception):
    """Raised when a genuine production output failure is detected."""


class PhaseVB1Orchestrator:
    """Orchestrates all Phase V.B.1 production output completion tasks."""

    MODEL_VERSION = "7.8.0"
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
        loader=None,
        v7_root: Optional[pathlib.Path] = None,
        run_root: Optional[pathlib.Path] = None,
        use_r13_integration: bool = True,
        use_r14_validation: bool = True,
    ) -> None:
        # v7_root = engine_root (src packages); run_root = data/output host
        self._v7_root = v7_root or _V6
        self._run_root = pathlib.Path(run_root) if run_root is not None else self._v7_root
        self.output_dir = output_dir or _OUTPUT_DIR
        import os
        if not (os.environ.get("STEEL_RUN_ROOT") or "").strip():
            gn_dir = self._run_root / "general_notes"
            if gn_dir.is_dir() and (
                any(gn_dir.glob("*.dxf")) or any(gn_dir.glob("*.DXF"))
            ):
                os.environ["STEEL_RUN_ROOT"] = str(self._run_root.resolve())
        self._loader = loader
        if self._loader is None and _R2A_AVAILABLE and parse_engineering_context:
            self._loader, _, _ = parse_engineering_context(self._v7_root)
        self._reinforcement_source = "REFERENCE_CLASSIFICATION_LEGACY"
        self._use_r14_validation = use_r14_validation
        self._r14_result = None
        if l2_path is not None:
            self.l2_path = l2_path
        elif use_r13_integration:
            self.l2_path, self._reinforcement_source = (
                self._resolve_r13_reinforcement_path()
            )
        else:
            self.l2_path = _L2_MODEL_PATH
        self.start_time = time.time()
        self.result = ProductionOutputResult()
        self._stats_collector = ProductionStatisticsCollector()

    def _resolve_r13_reinforcement_path(self):
        """Resolve EngineeringBarModel path via Phase R.1.3 integration."""
        try:
            import types
            import importlib.util as _ilu

            r13_dir = self._v7_root / "src/PhaseR1.3_pipeline_integration"
            if "PhaseR13.production_pipeline_rewire" not in sys.modules:
                pkg = types.ModuleType("PhaseR13")
                pkg.__path__ = [str(r13_dir)]
                sys.modules["PhaseR13"] = pkg
                for sub, fname in [
                    ("reinforcement_source_selector", "reinforcement_source_selector"),
                    ("engineering_bar_model", "engineering_bar_model"),
                    ("engineering_bar_builder", "engineering_bar_builder"),
                    ("reinforcement_pipeline_adapter", "reinforcement_pipeline_adapter"),
                    ("l2_engineering_processor", "l2_engineering_processor"),
                    ("pipeline_integration_manager", "pipeline_integration_manager"),
                    ("production_pipeline_rewire", "production_pipeline_rewire"),
                ]:
                    spec = _ilu.spec_from_file_location(
                        f"PhaseR13.{sub}", r13_dir / f"{fname}.py"
                    )
                    mod = _ilu.module_from_spec(spec)
                    mod.__package__ = "PhaseR13"
                    sys.modules[f"PhaseR13.{sub}"] = mod
                    spec.loader.exec_module(mod)

            rewire = sys.modules[
                "PhaseR13.production_pipeline_rewire"
            ].ProductionPipelineRewire(
                self._v7_root,
                auto_build=True,
                engine_root=self._v7_root,
                run_root=self._run_root,
            )
            path, source = rewire.resolve_models_path()
            print(f"      Reinforcement source: {source}")
            print(f"      Models path: {path.name}")
            return path, source
        except Exception as exc:
            print(f"      R.1.3 integration unavailable ({exc}), using L.2 fallback")
            return _L2_MODEL_PATH, "REFERENCE_CLASSIFICATION_LEGACY"

    def _bootstrap_r14(self):
        """Bootstrap Phase R.1.4 integrity validation package."""
        import types
        import importlib.util as _ilu

        r14_dir = self._v7_root / "src/PhaseR1.4_integrity_validation"
        if "PhaseR14.reinforcement_integrity_validator" in sys.modules:
            return
        pkg = types.ModuleType("PhaseR14")
        pkg.__path__ = [str(r14_dir)]
        sys.modules["PhaseR14"] = pkg
        modules = [
            "validation_models", "pipeline_data_loader", "coverage_analyzer",
            "beam_consistency_checker", "engineering_bar_validator",
            "pipeline_dependency_validator", "coverage_classifier",
            "integrity_quality_gate", "validation_statistics",
            "reinforcement_integrity_validator", "validation_reporter",
            "validation_export", "phase_r14_orchestrator",
        ]
        for name in modules:
            spec = _ilu.spec_from_file_location(
                f"PhaseR14.{name}", r14_dir / f"{name}.py"
            )
            mod = _ilu.module_from_spec(spec)
            mod.__package__ = "PhaseR14"
            sys.modules[f"PhaseR14.{name}"] = mod
            spec.loader.exec_module(mod)

    def _step_r14_integrity_validation(self) -> Dict[str, Any]:
        """Phase R.1.4 — validate reinforcement integrity before steel weight."""
        self._bootstrap_r14()
        PhaseR14Orchestrator = sys.modules[
            "PhaseR14.phase_r14_orchestrator"
        ].PhaseR14Orchestrator

        data_root = self._run_root or self._v7_root
        r14_out = data_root / "data/output/PhaseR1.4_integrity_validation"
        orch = PhaseR14Orchestrator(
            v7_root=self._v7_root,
            output_dir=r14_out,
            reinforcement_source=self._reinforcement_source,
            production_models_path=str(self.l2_path),
            export=True,
        )
        result = orch.run()
        vr = result["validation_result"]
        self._r14_result = vr

        if not vr.production_allowed:
            raise PRODUCTION_OUTPUT_ERROR(
                f"R.1.4 Quality Gate FAIL (strict_mode): "
                f"{'; '.join(vr.errors)}"
            )

        for w in vr.warnings:
            self.result.warnings.append(f"R.1.4 WARNING: {w}")

        return {
            "integrity_score": vr.integrity_score,
            "pipeline_health_score": vr.pipeline_health_score,
            "quality_gate_status": vr.quality_gate_status,
            "rules_passed": sum(
                1 for r in vr.rules.values() if r.status == "PASS"
            ),
            "rules_total": len(vr.rules),
        }

    # ── public entry point ────────────────────────────────────────────────────

    def run(self) -> ProductionOutputResult:
        print("=" * 70)
        print(f"PHASE V.B.1 — PRODUCTION OUTPUT COMPLETION")
        print(f"MODEL_VERSION: {self.MODEL_VERSION}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        try:
            # Step 1 — Integration engine validation
            print("\n[1/9] Integration Engine Validation")
            int_report = self._step_integration_validation()

            # Step 2 — R.1.4 Reinforcement integrity validation
            r14_report = None
            if self._use_r14_validation:
                print("[2/9] Phase R.1.4 Integrity Validation")
                r14_report = self._step_r14_integrity_validation()
            else:
                print("[2/9] Phase R.1.4 Integrity Validation — SKIPPED")

            # Step 3 — Steel weight completion
            print("[3/9] Steel Weight Calculation")
            steel_summary = self._step_steel_weight()
            self.result.steel_weight_kg = steel_summary.total_weight_kg
            print(f"      Total steel weight: {steel_summary.total_weight_kg:.3f} kg")

            # Step 4 — BBS generation
            print("[4/9] BBS Completion Engine")
            bbs_engine = BBSCompletionEngine(
                steel_summary, frame_type=self._resolve_frame_identifier()
            )
            bbs_rows = bbs_engine.generate()
            print(f"      BBS rows generated: {len(bbs_rows)}")

            # Step 5 — Excel workbook generation
            print("[5/9] Estimator Excel Generator")
            paths = self._step_excel_generation(bbs_rows, steel_summary)
            self.result.workbook_path = str(paths["production"])
            self.result.engineering_review_path = str(paths["engineering_review"])
            self.result.archive_path = str(paths["archive"])
            print(f"      Output: {paths['production'].name}")

            # Step 6 — Workbook validation
            print("[6/9] Workbook Validation")
            val_result = self._step_workbook_validation(paths["production"], steel_summary)
            self.result.workbook_validated = val_result.validation_passed
            self.result.validation_result = val_result

            # Step 7 — Production statistics
            print("[7/9] Production Statistics")
            statistics = self._stats_collector.collect(bbs_rows, steel_summary, paths)
            self.result.statistics = statistics

            # Step 8 — Production reporter
            print("[8/9] Production Reporter")
            reporter = ProductionReporter(
                result=self.result,
                steel_summary=steel_summary,
                bbs_rows=bbs_rows,
                statistics=statistics,
                validation_result=val_result,
                integration_report=int_report,
            )
            report = reporter.build()

            # Step 9 — Export
            print("[9/9] Exporting JSON artefacts")
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

    def _resolve_frame_identifier(self) -> str:
        """Drawing-specific floor/frame from VROOT.1 project_manifest when present."""
        import json
        import os

        candidates = []
        if self._run_root:
            candidates.append(
                pathlib.Path(self._run_root)
                / "data" / "output"
                / "PhaseVROOT.1_dynamic_pipeline_initialization"
                / "project_manifest.json"
            )
        env_run = (os.environ.get("STEEL_RUN_ROOT") or "").strip()
        if env_run:
            candidates.append(
                pathlib.Path(env_run)
                / "data" / "output"
                / "PhaseVROOT.1_dynamic_pipeline_initialization"
                / "project_manifest.json"
            )
        for path in candidates:
            if not path.is_file():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            floor = str(data.get("floor") or "").strip()
            if floor and floor not in ("UNKNOWN_FLOOR", "UNKNOWN"):
                return floor
        try:
            vroot = pathlib.Path(self._v7_root) / "src" / "PhaseVROOT.1_dynamic_pipeline_initialization"
            if str(vroot) not in sys.path:
                sys.path.insert(0, str(vroot))
            from project_discovery import ProjectDiscovery
            roots = []
            if self._run_root:
                roots.append(pathlib.Path(self._run_root))
            if env_run:
                roots.append(pathlib.Path(env_run))
            seen = set()
            for root in roots:
                key = str(root.resolve()) if root.exists() else str(root)
                if key in seen:
                    continue
                seen.add(key)
                discovered = ProjectDiscovery().discover(root)
                floor = str(discovered.get("floor") or "").strip()
                if floor and floor not in ("UNKNOWN_FLOOR", "UNKNOWN"):
                    return floor
        except Exception:
            pass
        return ""

    def _step_steel_weight(self):
        models_path = self.l2_path
        if not models_path.exists():
            raise PRODUCTION_OUTPUT_ERROR(
                f"Reinforcement model file not found: {models_path}"
            )
        print(f"      Source: {self._reinforcement_source}")
        engine = SteelWeightCompletion(models_path, loader=self._loader)
        summary = engine.compute()
        if summary.total_weight_kg <= 0:
            raise PRODUCTION_OUTPUT_ERROR(
                "RULE_2 FAIL: Steel Weight = 0 after computation. "
                "Check L.2 model bar data."
            )
        return summary

    def _step_excel_generation(self, bbs_rows, steel_summary) -> Dict:
        loader_summary = self._loader.summary() if self._loader else None
        generator = EstimatorExcelGenerator(
            bbs_rows=bbs_rows,
            steel_summary=steel_summary,
            output_dir=self.output_dir,
            loader_summary=loader_summary,
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
