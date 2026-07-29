"""
Phase SI.0 Orchestrator — Stirrup Recovery & Interpretation Engine
MODEL_VERSION: 6.6.2

Pipeline:
  1. Load L.2 beam_reinforcement_models.json
  2. Load annotation_features.json (L.2.1)
  3. Find stirrup candidates in ALL annotations (MODULE 1)
  4. For each beam: validate existing stirrups (MODULE 4)
  5. Recover invalid stirrups (MODULE 5)
  6. Build updated beam models (MODULE 7)
  7. Validate updated models (MODULE 8)
  8. Compute statistics (MODULE 9)
  9. Generate report (MODULE 10)
  10. Export artefacts + updated beam_reinforcement_models.json (MODULE 11)

The updated beam_reinforcement_models.json is written to the SI.0 output
directory and is referenced by SI.1 when SI.0 has been applied.
"""
import json
import pathlib
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

_SRC = pathlib.Path(__file__).parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from si0_stirrup_recovery_models import (
    BeamRecoveryResult, SI0EngineResult,
    RecoveryDecision, RecoverySource,
)
from si0_stirrup_candidate_finder import StirrupCandidateFinder
from si0_stirrup_recovery_engine import StirrupRecoveryEngine
from si0_beam_reinforcement_updater import BeamReinforcementUpdater
from si0_stirrup_quality_validator import validate_updated_models
from si0_stirrup_statistics import compute_statistics
from si0_stirrup_reporter import StirrupRecoveryReporter
from si0_stirrup_export import StirrupRecoveryExport

_V6       = pathlib.Path(__file__).parents[3] / "Version8"
_L2_PATH  = (
    _V6 / "data/output/PhaseL.2 - engineering_reinforcement_interpretation"
    / "beam_reinforcement_models.json"
)
_AF_PATH  = (
    _V6 / "data/output/PhaseL.2.1 - engineering_feature_extraction"
    / "annotation_features.json"
)
_OUT_DIR  = _V6 / "data/output/PhaseSI.0_stirrup_recovery"


class PhaseSI0Orchestrator:
    """Full SI.0 orchestration — can be run standalone or from the runner."""

    MODEL_VERSION = "6.6.2"

    def __init__(
        self,
        l2_path: Optional[pathlib.Path] = None,
        annotation_path: Optional[pathlib.Path] = None,
        output_dir: Optional[pathlib.Path] = None,
    ) -> None:
        self.l2_path   = l2_path or _L2_PATH
        self.af_path   = annotation_path or _AF_PATH
        self.out_dir   = output_dir or _OUT_DIR

    def run(self) -> SI0EngineResult:
        print("=" * 70)
        print("PHASE SI.0 - STIRRUP RECOVERY & INTERPRETATION ENGINE")
        print(f"MODEL_VERSION: {self.MODEL_VERSION}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        # ── Load inputs ──────────────────────────────────────────────────────
        l2_data = json.loads(self.l2_path.read_text(encoding="utf-8"))
        models  = l2_data.get("models", [])
        print(f"\nL.2 models loaded:         {len(models)}")

        af_data  = json.loads(self.af_path.read_text(encoding="utf-8"))
        af_items = af_data.get("features", []) if isinstance(af_data, dict) else af_data
        print(f"Annotation features loaded: {len(af_items)}")

        # ── MODULE 1: Find candidates ─────────────────────────────────────────
        finder     = StirrupCandidateFinder()
        candidates = finder.find_all(af_items)
        print(f"Valid stirrup candidates:   {len(candidates)}")

        # ── MODULE 4+5: Validate & Recover ────────────────────────────────────
        engine       = StirrupRecoveryEngine()
        beam_results: List[BeamRecoveryResult] = []
        for model in models:
            result = engine.recover_beam(model, candidates)
            beam_results.append(result)

        # ── MODULE 7: Build updated models ────────────────────────────────────
        updater        = BeamReinforcementUpdater()
        updated_models = updater.apply(models, beam_results)

        # ── MODULE 8: Quality validation ──────────────────────────────────────
        passed, errors = validate_updated_models(updated_models, recovery_results_generated=True)

        # ── MODULE 9: Statistics ──────────────────────────────────────────────
        stats = compute_statistics(beam_results, total_beams=len(models))

        # ── MODULE 10: Report ─────────────────────────────────────────────────
        reporter = StirrupRecoveryReporter(beam_results, stats, passed, errors)
        report   = reporter.build()

        # ── MODULE 11: Export ─────────────────────────────────────────────────
        exporter = StirrupRecoveryExport(self.out_dir)
        paths    = exporter.export_all(
            report=report,
            statistics=stats,
            beam_results=beam_results,
            updated_models=updated_models,
            candidates=candidates,
            l2_wrapper=l2_data,
        )

        # ── Aggregate result ──────────────────────────────────────────────────
        result = SI0EngineResult(
            total_beams=len(models),
            beams_with_stirrups=sum(1 for r in beam_results if r.source != RecoverySource.NO_STIRRUP),
            invalid_stirrups_found=sum(1 for r in beam_results if r.invalid_reason is not None),
            benchmark_retained=sum(1 for r in beam_results if r.source == RecoverySource.BENCHMARK),
            recovered_from_annotation=stats["recovery_by_source"].get("ANNOTATION", 0),
            recovered_from_shared_group=stats["recovery_by_source"].get("SHARED_GROUP", 0),
            recovered_from_proximity=stats["recovery_by_source"].get("PROXIMITY", 0),
            recovered_from_inference=stats["recovery_by_source"].get("ENGINEERING_INFERENCE", 0),
            beam_results=beam_results,
            validation_passed=passed,
            validation_errors=errors,
        )

        self._print_summary(result, paths, stats)

        return result

    def _print_summary(
        self,
        result: SI0EngineResult,
        paths: Dict[str, pathlib.Path],
        stats: Dict,
    ) -> None:
        print("\n" + "=" * 70)
        print("PHASE SI.0 COMPLETE")
        print("=" * 70)
        print(f"  Total beams:              {result.total_beams}")
        print(f"  Beams with stirrups:      {result.beams_with_stirrups}")
        print(f"  Invalid stirrups found:   {result.invalid_stirrups_found}")
        print(f"  Benchmark beams retained: {result.benchmark_retained}")
        print(f"  Recovered (annotation):   {result.recovered_from_annotation}")
        print(f"  Recovered (shared group): {result.recovered_from_shared_group}")
        print(f"  Recovered (proximity):    {result.recovered_from_proximity}")
        print(f"  Recovered (inference):    {result.recovered_from_inference}")
        print(f"\n  Validation: {'PASS' if result.validation_passed else 'FAIL'}")
        if result.validation_errors:
            for e in result.validation_errors:
                print(f"    ERROR: {e}")
        print(f"\n  Updated model:  {paths.get('beam_reinforcement_models', '')}")
        print(f"  JSON exports:   {len(paths)} files -> {self.out_dir}")
        print("=" * 70)
