"""
Runner — Phase V.TEST.3 Benchmark Set 3 Generalization Validation
MODEL_VERSION: 8.1.1

Usage:
    cd Version7
    python Run_PY/run_phase_vtest3_benchmark_set3_validation.py

READ-ONLY validation. Executes complete pipeline on Third Set Drawings.
No engineering logic modified.
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parent
_V7         = _RUNNER_DIR.parent
_VTEST_SRC  = _V7 / "src/PhaseVTEST3_benchmark_set3_validation"

for _p in [str(_VTEST_SRC), str(_V7)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(_V7)


def main() -> None:
    from phase_vtest3_orchestrator import (
        PhaseVTEST3Orchestrator,
        BENCHMARK_SET3_VALIDATION_ERROR,
    )

    print()
    try:
        result = PhaseVTEST3Orchestrator().run()

        print()
        print("=" * 72)
        print("FINAL DELIVERY SUMMARY — Phase V.TEST.3")
        print("=" * 72)

        if result.manifest:
            print(f"  Project            : {result.manifest.project_name}")
            print(f"  Building / Floor   : {result.manifest.building} / {result.manifest.floor}")
            print(f"  Input files        : {result.manifest.total_files}")
            print(f"  DXF files          : {result.manifest.dxf_count}")

        if result.pipeline:
            print(f"  Pipeline stages    : {result.pipeline.stages_passed}/"
                  f"{result.pipeline.stages_executed} passed")
            print(f"  Pipeline elapsed   : {result.pipeline.total_elapsed_seconds:.1f}s")

        print(f"  Total beams        : {result.beam_summary.get('total_beams', 0)}")
        print(f"  Annotations        : {result.reinforcement_summary.get('reinforcement_annotations', 0)}")
        print(f"  Steel (kg)         : {result.production_summary.get('steel_quantity_kg', 0):.2f}")
        print(f"  Workbook           : {result.production_summary.get('workbook_generated', False)}")
        print(f"  Readiness score    : {result.overall_readiness_score}/100")
        print(f"  Classification     : {result.readiness_classification}")
        print(f"  Generalization     : {result.generalization_audit.get('summary', 'N/A')}")

        passed = sum(
            1 for v in result.validation_rules.values()
            if (v.get("passed") if isinstance(v, dict) else v)
        )
        print(f"  Validation rules   : {passed}/{len(result.validation_rules)} passed")
        print()

        out_dir = _V7 / "data/output/PhaseVTEST3_generalization_validation"
        print(f"  Artefacts dir      : {out_dir}")
        print()

        if result.overall_passed:
            print("[COMPLETE] Phase V.TEST.3 — All validation rules passed.")
        else:
            failed = [
                k for k, v in result.validation_rules.items()
                if not (v.get("passed") if isinstance(v, dict) else v)
            ]
            print(f"[COMPLETE] Phase V.TEST.3 finished. Failed rules: {failed}")

        if result.warnings:
            print(f"\n  Warnings ({len(result.warnings)}):")
            for w in result.warnings[:8]:
                print(f"    - {w}")

        print()
        print(f"  Recommended next   : {result.recommended_next_phase}")
        print("=" * 72)

        sys.exit(0 if result.overall_passed else 1)

    except BENCHMARK_SET3_VALIDATION_ERROR as err:
        print(f"\n[BENCHMARK_SET3_VALIDATION_ERROR] {err}")
        sys.exit(2)
    except Exception as exc:
        import traceback
        print(f"\n[ERROR] Unexpected error: {exc}")
        traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    main()
