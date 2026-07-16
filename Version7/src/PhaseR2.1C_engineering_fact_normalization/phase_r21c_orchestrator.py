"""
phase_r21c_orchestrator.py — Master orchestrator for Phase R.2.1C.
MODEL_VERSION: 7.12.0

Execution sequence:
  1. Load R.2.1B EngineeringSemanticObjects
  2. Build EngineeringFact for each ESO
  3. Validate (12 rules)
  4. Compute statistics
  5. Generate report
  6. Export all artefacts

This phase is entirely additive:
  - No existing production modules are modified.
  - No existing output files are overwritten.
  - Pipeline compatibility is verified (RULE_12).
"""
from __future__ import annotations

import json
import pathlib
from datetime import datetime
from typing import Any, Dict, List, Optional

from .engineering_fact_builder import EngineeringFactBuilder
from .fact_export import FactExport
from .fact_models import EngineeringFact
from .fact_reporter import FactReporter
from .fact_statistics import FactStatistics
from .fact_validation import FactValidation

MODEL_VERSION = "7.12.0"
PHASE_ID = "R.2.1C"

# ── Default paths (relative to Version7 root) ────────────────────────────────
_V7  = pathlib.Path(__file__).parent.parent.parent          # …/Version7
_ESO_PATH = (
    _V7 / "data/output/PhaseR2.1B_engineering_semantic_interpreter"
    / "engineering_semantic_objects.json"
)
_OUTPUT_DIR = _V7 / "data/output/PhaseR2.1C_engineering_fact_normalization"

# Production workbook verification path
_WORKBOOK_GLOB_PATTERN = "*.xlsx"
_VB1_OUTPUT_DIR = _V7 / "data/output/PhaseVB.1_production_output_completion"


class PhaseR21COrchestrator:
    """
    Master orchestrator for Phase R.2.1C — Engineering Fact Normalization Engine.
    """

    def __init__(
        self,
        eso_path:   Optional[pathlib.Path] = None,
        output_dir: Optional[pathlib.Path] = None,
    ):
        self.eso_path   = pathlib.Path(eso_path)   if eso_path   else _ESO_PATH
        self.output_dir = pathlib.Path(output_dir) if output_dir else _OUTPUT_DIR

        self._builder   = EngineeringFactBuilder()
        self._validator = FactValidation()
        self._statter   = FactStatistics()
        self._reporter  = FactReporter()
        self._exporter  = FactExport()

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self) -> Dict[str, Any]:
        start = datetime.now()
        print(f"[R.2.1C] Engineering Fact Normalization Engine — MODEL_VERSION {MODEL_VERSION}")
        print(f"[R.2.1C] Phase: {PHASE_ID}")
        print(f"[R.2.1C] Input: {self.eso_path}")
        print(f"[R.2.1C] Output: {self.output_dir}")
        print()

        # Step 1: Load R.2.1B semantic objects
        esos_by_beam = self._load_esos()
        total_esos = sum(len(v) for v in esos_by_beam.values())
        print(f"[R.2.1C] Loaded {total_esos} semantic objects from {len(esos_by_beam)} beams")

        # Step 2: Build EngineeringFacts
        facts_by_beam = self._builder.build_all(esos_by_beam)
        total_facts   = sum(len(v) for v in facts_by_beam.values())
        print(f"[R.2.1C] Built {total_facts} EngineeringFacts")

        # Step 3: Validate
        workbook_path = self._find_production_workbook()
        validation    = self._validator.validate(facts_by_beam, esos_by_beam, workbook_path)
        v_summary     = validation.get("summary", "")
        v_all_pass    = validation.get("all_pass", False)
        status_icon   = "OK" if v_all_pass else "FAIL"
        print(f"[R.2.1C] Validation: [{status_icon}] {v_summary}")

        # Step 4: Statistics
        stats = self._statter.compute(facts_by_beam)
        print(f"[R.2.1C] Intent UNKNOWN: {stats['intent_unknown_count']}/{total_facts} "
              f"({stats['intent_unknown_pct']}%)")
        print(f"[R.2.1C] Role coverage:  {stats['role_coverage_pct']}%")
        print(f"[R.2.1C] Placement cov:  {stats['placement_coverage_pct']}%")

        # Step 5: Report
        report_md = self._reporter.generate(facts_by_beam, stats, validation)

        # Step 6: Export
        self.output_dir.mkdir(parents=True, exist_ok=True)
        exported_paths = self._exporter.export_all(
            facts_by_beam, stats, validation, report_md, self.output_dir
        )
        print(f"[R.2.1C] Exported {len(exported_paths)} artefacts to {self.output_dir}")

        elapsed = (datetime.now() - start).total_seconds()
        result = {
            "phase_id":           PHASE_ID,
            "model_version":      MODEL_VERSION,
            "beam_count":         len(facts_by_beam),
            "total_facts":        total_facts,
            "validation":         validation,
            "statistics":         stats,
            "exported_artefacts": {k: str(v) for k, v in exported_paths.items()},
            "elapsed_seconds":    round(elapsed, 2),
            "success":            v_all_pass,
        }

        print()
        print(f"[R.2.1C] Completed in {elapsed:.2f}s — {v_summary}")
        if not v_all_pass:
            self._print_failures(validation)

        return result

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_esos(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load EngineeringSemanticObjects from R.2.1B output JSON."""
        if not self.eso_path.exists():
            raise FileNotFoundError(
                f"R.2.1B output not found: {self.eso_path}\n"
                "Run Phase R.2.1B first: python Version7/Run_PY/run_phase_r21b_semantic_interpreter.py"
            )
        with self.eso_path.open(encoding="utf-8") as f:
            data = json.load(f)

        # Support both {"by_beam": {...}} and raw dict structures
        if isinstance(data, dict) and "by_beam" in data:
            return data["by_beam"]
        if isinstance(data, dict):
            # Assume top-level keys are beam IDs
            return data
        raise ValueError(f"Unexpected ESO JSON structure in {self.eso_path}")

    def _find_production_workbook(self) -> Optional[pathlib.Path]:
        """Find the production workbook to validate pipeline compatibility."""
        # Check multiple known output locations
        candidates = [
            _VB1_OUTPUT_DIR,
            _V7 / "data/output/Production_Output",
            _V7 / "data/output/PhaseR.1.1_production_validation",
        ]
        for candidate_dir in candidates:
            if candidate_dir.exists():
                xlsx_files = sorted(candidate_dir.glob(_WORKBOOK_GLOB_PATTERN))
                if xlsx_files:
                    return xlsx_files[0]
        return None

    @staticmethod
    def _print_failures(validation: Dict[str, Any]) -> None:
        rules = validation.get("rules", {})
        for rule_id, result in rules.items():
            if not result["passed"]:
                print(f"  [FAIL] {rule_id}: {result['detail']}")
