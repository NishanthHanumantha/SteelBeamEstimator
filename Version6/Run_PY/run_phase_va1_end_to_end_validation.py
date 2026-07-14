"""
Phase V.A.1 — End-to-End Validation
Runner script.
MODEL_VERSION: 6.5.3
"""
from __future__ import annotations

import pathlib
import sys
import traceback

MODEL_VERSION = "6.5.3"

_PACKAGE_DIR = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "PhaseVA.1_end_to_end_validation"
)
if str(_PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_DIR))


def main() -> None:
    print("=" * 72)
    print("Phase V.A.1 — End-to-End Engineering Validation")
    print(f"MODEL_VERSION: {MODEL_VERSION}")
    print("=" * 72)
    print("OBJECTIVE: Validate complete production pipeline end-to-end.")
    print("MODE: Read-only. No engineering modifications.")
    print("=" * 72)

    from phase_va1_orchestrator import PhaseVA1Orchestrator

    orchestrator = PhaseVA1Orchestrator()
    try:
        result = orchestrator.run()
    except Exception as exc:
        print(f"\n[ERROR] Phase V.A.1 failed: {exc}")
        traceback.print_exc()
        sys.exit(1)

    # ── Print summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("PHASE V.A.1 — VALIDATION RESULTS")
    print("=" * 72)
    print(f"  Benchmark ID       : {result['benchmark_id']}")
    print(f"  Drawing            : {result['drawing_name']}")
    print(f"  MODEL_VERSION      : {result['model_version']}")

    print(f"\n  Pipeline Execution:")
    print(f"    Stages Executed  : {result['stages_executed']}")
    print(f"    Stages Passed    : {result['stages_passed']}")
    print(f"    Total Time (s)   : {result['total_pipeline_seconds']}")

    print(f"\n  Workbook Generation:")
    print(f"    Generated        : {result['workbook_generated']}")
    print(f"    Valid            : {result['workbook_valid']}")
    print(f"    Size             : {result['workbook_size_kb']} KB")
    print(f"    Sheets           : {result['workbook_sheets']}")

    print(f"\n  Worksheet Validation:")
    print(f"    Pass Rate        : {result['worksheet_pass_rate_pct']}%")

    print(f"\n  Workbook Comparison:")
    print(f"    Match Rate       : {result['comparison_match_rate_pct']}%")
    print(f"    Totals Match     : {result['totals_match']}")
    sw = result.get("steel_weight_comparison", {})
    if sw:
        print(f"    Steel (gen/ref)  : {sw.get('generated_total', 0)} / {sw.get('reference_total', 0)} kg")
        print(f"    Steel Diff       : {sw.get('difference_pct', 'N/A')}%")

    print(f"\n  Validation Rules:")
    for rule, passed in result.get("rule_results", {}).items():
        print(f"    [{'PASS' if passed else 'FAIL'}] {rule}")

    if result.get("engineering_differences"):
        print(f"\n  Engineering Differences Observed:")
        for diff in result["engineering_differences"][:5]:
            print(f"    - {diff[:120]}")

    if result.get("blockers"):
        print(f"\n  Blockers:")
        for b in result["blockers"]:
            print(f"    ! {b[:120]}")

    print(f"\n  Recommendations:")
    for rec in result.get("recommendations", [])[:3]:
        print(f"    -> {rec[:120]}")

    print(f"\n  Ready for Benchmark Set 2: {result['ready_for_benchmark_set_2']}")
    print(f"  Overall Validation: {'PASS' if result['validation_passed'] else 'PARTIAL'}")

    print(f"\n  Exported Artefacts:")
    for name in result.get("exported_paths", {}):
        print(f"    {name}")

    print("\n" + "=" * 72)
    print(f"Phase V.A.1 complete — MODEL_VERSION {MODEL_VERSION}")
    print("=" * 72)


if __name__ == "__main__":
    main()
