"""
Phase R.1.6.2 orchestrator — RULE-012 Mandatory Stirrup Coverage Validation.
MODEL_VERSION: 8.8.2
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional

from coverage_engine import CoverageEngine
from coverage_report_builder import CoverageReportBuilder
from coverage_validation_engine import CoverageValidationEngine
from mandatory_stirrup_validator import MandatoryStirrupValidator
from rule012_library_updater import Rule012LibraryUpdater

MODEL_VERSION = "8.8.2"
PHASE_ID = "R.1.6.2"


class PhaseR162Orchestrator:
    def __init__(self, v8_root: Optional[Path] = None):
        self.v8 = Path(v8_root) if v8_root else Path(__file__).resolve().parents[2]
        self.out = self.v8 / "data" / "output" / "PhaseR1_6_2_stirrup_coverage_validation"
        self.library_dir = self.v8 / "data" / "output" / "PhaseR1_6_engineering_rule_synthesis"
        self.package_dir = Path(__file__).resolve().parent

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print("Phase R.1.6.2 — RULE-012 Mandatory Stirrup Coverage Validation")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print("DETECTION ONLY — no auto-correction / no production modification")
        print("=" * 72)
        t0 = time.perf_counter()

        print("\n[1/7] Loading Beam Registry + pipeline artefacts ...")
        engine = CoverageEngine(self.v8)
        inputs = engine.load_inputs()
        beam_ids = inputs["beam_ids"]
        print(f"      Beams={len(beam_ids)}")
        if not beam_ids:
            raise RuntimeError("Beam Registry empty — run V.ROOT.1 first.")

        print("\n[2/7] Validating mandatory stirrup coverage per beam ...")
        validator = MandatoryStirrupValidator()
        records = validator.validate_all(inputs)
        diagnostics = validator.diagnostics(records)
        metrics = engine.compute_metrics(
            beam_ids,
            inputs["stage_stirrup"],
            [r.to_dict() for r in records],
        )
        print(
            f"      Coverage={metrics.coverage_pct}% "
            f"({metrics.detected_stirrup_families}/{metrics.beam_count}) "
            f"PASS={metrics.pass_count} FAIL={metrics.fail_count}"
        )

        print("\n[3/7] Updating Engineering Rule Library with RULE-012 ...")
        lib_update = Rule012LibraryUpdater(self.library_dir).update(
            missing_beam_ids=[r.beam_id for r in records if r.status == "FAIL"]
        )
        print(f"      Library rules={lib_update.get('rule_count')} files={len(lib_update.get('updated_files') or [])}")

        print("\n[4/7] Validation ...")
        ve = CoverageValidationEngine()
        validation = ve.validate(records, metrics, inputs, self.package_dir)
        print(f"      Validation {validation['passed']}/{validation['total']}")

        print("\n[5/7] Regression (Benchmark Sets 1–3 structural) ...")
        regression = ve.regression(self.v8, self.package_dir, metrics)
        print(f"      Regression passed={regression.get('passed')}")

        # Recommendation B if any coverage failure remains.
        recommendation = "A" if (
            validation.get("overall_passed")
            and regression.get("passed")
            and metrics.fail_count == 0
            and metrics.coverage_pct >= 100.0
        ) else "B"

        elapsed = round(time.perf_counter() - t0, 2)
        print("\n[6/7] Exporting artefacts ...")
        paths = CoverageReportBuilder(self.out).build_all(
            records=records,
            metrics=metrics,
            diagnostics=diagnostics,
            validation=validation,
            regression=regression,
            rule012=lib_update["rule"],
            sources=inputs["sources"],
            recommendation=recommendation,
            elapsed_s=elapsed,
        )
        print(f"      Exported={len(paths)} → {self.out}")

        print("\n[7/7] Complete.")
        status = "PASS" if validation.get("overall_passed") and regression.get("passed") else "WARN"
        # Coverage failures are expected findings; validation of the detector can still PASS.
        if metrics.fail_count > 0:
            status = "WARN"

        result = {
            "model_version": MODEL_VERSION,
            "phase": PHASE_ID,
            "status": status,
            "recommendation": recommendation,
            "metrics": metrics.to_dict(),
            "validation": validation,
            "regression": regression,
            "library_update": {
                "rule_count": lib_update.get("rule_count"),
                "updated_files": lib_update.get("updated_files"),
            },
            "missing_count": len(diagnostics),
            "export_paths": paths,
            "elapsed_s": elapsed,
        }
        self._print_summary(result)
        return result

    @staticmethod
    def _print_summary(result: Dict[str, Any]) -> None:
        m = result.get("metrics") or {}
        print("\n" + "-" * 72)
        print(f"  PHASE {result.get('phase')} RULE-012 SUMMARY")
        print(f"  Status           : {result.get('status')}")
        print(f"  Beams            : {m.get('beam_count')}")
        print(f"  Stirrup families : {m.get('detected_stirrup_families')}")
        print(f"  Coverage %       : {m.get('coverage_pct')}")
        print(f"  Fail / Missing % : {m.get('fail_count')} / {m.get('missing_pct')}")
        print(f"  Validation       : {result.get('validation', {}).get('passed')}/"
              f"{result.get('validation', {}).get('total')}")
        print(f"  Recommendation   : {result.get('recommendation')}")
        print("-" * 72)
