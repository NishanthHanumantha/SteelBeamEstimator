"""
Runner -- Phase V.A.2 End-to-End Validation (Benchmark Set 2)
MODEL_VERSION : 7.0.0

Usage:
    cd Version8
    python Run_PY/run_phase_va2_benchmark_set2_validation.py
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

# ---- Environment bootstrap --------------------------------------------------
_RUNNER_DIR = Path(__file__).resolve().parent
_V7         = _RUNNER_DIR.parent                         # Version8/
_VA2_SRC    = _V7 / "src/PhaseVA.2_benchmark_set2_validation"

for _p in [str(_VA2_SRC), str(_V7)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(_V7)
# -----------------------------------------------------------------------------


def main() -> None:
    from phase_va2_orchestrator import PhaseVA2Orchestrator, BENCHMARK_SET2_VALIDATION_ERROR

    print()
    try:
        orchestrator = PhaseVA2Orchestrator()
        result       = orchestrator.run()

        ga    = result.generalization_assessment or {}
        rules = result.rules_passed

        print()
        print("=" * 72)
        print("FINAL DELIVERY SUMMARY")
        print("=" * 72)

        manifest = result.manifest
        if manifest:
            print(f"  Drawing            : {manifest.drawing_name}")
            print(f"  Input files        : {manifest.total_files}")
            print(f"  Estimator Excel    : {manifest.has_estimator_excel}")

        pipeline = result.pipeline
        if pipeline:
            print(f"  Pipeline stages    : {pipeline.stages_passed}/{pipeline.stages_executed} passed")
            print(f"  Pipeline elapsed   : {pipeline.total_elapsed_seconds:.1f}s")

        wv = result.workbook_validation
        if wv:
            print(f"  Workbook exists    : {wv.exists}")
            print(f"  Workbook sheets    : {wv.total_sheets}")

        kpis = result.engineering_kpis
        if kpis:
            print(f"  Total beams        : {kpis.total_beams}")
            print(f"  Total steel (kg)   : {kpis.total_steel_kg}")
            print(f"  Stirrup coverage   : {kpis.stirrup_coverage_beams} beams")
            print(f"  BBS completeness   : {kpis.bbs_completeness_pct}%")

        print(f"  Generalization     : {ga.get('classification', 'UNKNOWN')} "
              f"(score={ga.get('overall_score', 0):.1f}/100)")
        print(f"  Overall passed     : {result.overall_passed}")
        print()

        print("  Rules:")
        for r, p in sorted(rules.items()):
            icon = "PASS" if p else "FAIL"
            print(f"    [{icon}]  {r}")
        print()

        out_dir = _V7 / "data/output/PhaseVA.2_benchmark_set2_validation"
        print(f"  Artefacts dir      : {out_dir}")

        wb_path = _V7 / "data/output/Production_Output/Estimation_Output.xlsx"
        print(f"  Estimation_Output  : {wb_path}")
        print(f"  Workbook exists    : {wb_path.exists()}")

        print()
        if result.overall_passed:
            print("[COMPLETE]  Phase V.A.2 -- All 7 rules passed.")
        else:
            failed = [k for k, v in rules.items() if not v]
            print(f"[COMPLETE]  Phase V.A.2 finished. Failed rules: {failed}")
            print("  Failures are documented in the report -- no engineering logic modified.")

        sys.exit(0 if result.overall_passed else 1)

    except BENCHMARK_SET2_VALIDATION_ERROR as err:
        print(f"\n[BENCHMARK_SET2_VALIDATION_ERROR] {err}")
        sys.exit(2)
    except Exception as exc:
        import traceback
        print(f"\n[ERROR] Unexpected error: {exc}")
        traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    main()
