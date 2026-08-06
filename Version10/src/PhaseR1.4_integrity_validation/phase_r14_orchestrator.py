"""Phase R.1.4 master orchestrator."""
from __future__ import annotations
import pathlib
import time
from datetime import datetime
from typing import Any, Dict, Optional

from .reinforcement_integrity_validator import ReinforcementIntegrityValidator
from .validation_export import ValidationExport
from .validation_reporter import ValidationReporter
from .validation_models import ValidationResult


class PhaseR14Orchestrator:

    MODEL_VERSION = "7.8.0"

    def __init__(
        self,
        v7_root: pathlib.Path,
        output_dir: Optional[pathlib.Path] = None,
        reinforcement_source: str = "",
        production_models_path: str = "",
        export: bool = True,
    ):
        self._v7 = v7_root
        self._out = output_dir or (
            v7_root / "data/output/PhaseR1.4_integrity_validation"
        )
        self._source = reinforcement_source
        self._prod_path = production_models_path
        self._export = export

    def run(self) -> Dict[str, Any]:
        t0 = time.perf_counter()
        print(f"\n{'='*70}")
        print("  PHASE R.1.4 — Reinforcement Integrity & Coverage Validation")
        print(f"  MODEL_VERSION {self.MODEL_VERSION}  |  {datetime.utcnow().isoformat()}")
        print(f"{'='*70}\n")

        print("[1/4] Loading Beam Registry and EngineeringBarModel ...")
        validator = ReinforcementIntegrityValidator(
            self._v7,
            reinforcement_source=self._source,
            production_models_path=self._prod_path,
        )

        print("[2/4] Running integrity validators ...")
        result = validator.validate()

        print("[3/4] Generating reports ...")
        reporter = ValidationReporter()
        reporter.print_console(result)
        engineering_summary = reporter.build_engineering_summary(result)
        markdown = reporter.build_markdown(result)

        export_paths: Dict[str, str] = {}
        if self._export:
            print("\n[4/4] Exporting artefacts ...")
            export_paths = ValidationExport(self._out).export_all(
                result, engineering_summary, markdown
            )
        else:
            print("\n[4/4] Export skipped (embedded production run)")

        elapsed = round(time.perf_counter() - t0, 3)
        status = "PASS" if result.all_rules_passed else "FAIL"
        if not result.production_allowed:
            status = "FAIL"

        print(f"\n{'='*70}")
        print(f"  PHASE R.1.4 COMPLETE — {status}")
        print(f"  Integrity: {result.integrity_score}  |  "
              f"Health: {result.pipeline_health_score}")
        print(f"  Quality Gate: {result.quality_gate_status}  |  "
              f"Time: {elapsed}s")
        print(f"{'='*70}\n")

        return {
            "status": status,
            "model_version": self.MODEL_VERSION,
            "validation_result": result,
            "engineering_summary": engineering_summary,
            "export_paths": export_paths,
            "elapsed_seconds": elapsed,
        }

    @staticmethod
    def run_integrity_check(
        v7_root: pathlib.Path,
        reinforcement_source: str,
        production_models_path: str,
        export: bool = False,
    ) -> ValidationResult:
        """Lightweight entry for VB1 production integration."""
        orch = PhaseR14Orchestrator(
            v7_root=v7_root,
            reinforcement_source=reinforcement_source,
            production_models_path=production_models_path,
            export=export,
        )
        return orch.run()["validation_result"]
