"""
Phase QA.1.1 — Engineering Error Diagnostics & Root Cause Analysis Engine
Runner script.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

import sys
import pathlib
import json
import traceback

MODEL_VERSION = "6.5.2"

# Bootstrap: add package directory to sys.path so absolute imports work
_PACKAGE_DIR = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "PhaseQA.1.1_engineering_error_diagnostics"
)
if str(_PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_DIR))


def main() -> None:
    print("=" * 72)
    print("Phase QA.1.1 — Engineering Error Diagnostics & Root Cause Analysis")
    print(f"MODEL_VERSION: {MODEL_VERSION}")
    print("=" * 72)

    from phase_qa11_orchestrator import PhaseQA11Orchestrator

    orchestrator = PhaseQA11Orchestrator()

    try:
        result = orchestrator.run()
    except Exception as exc:
        print(f"\n[ERROR] Phase QA.1.1 failed: {exc}")
        traceback.print_exc()
        sys.exit(1)

    # ── Print summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("PHASE QA.1.1 — DIAGNOSTIC RESULTS")
    print("=" * 72)
    print(f"  Benchmark ID     : {result['benchmark_id']}")
    print(f"  Drawing          : {result['drawing_name']}")
    print(f"  Total Diagnostics: {result['total_diagnostics']}")
    print(f"  Validation Passed: {result['validation_passed']}")
    print(f"  MODEL_VERSION    : {result['model_version']}")

    print("\n  Root Cause Distribution:")
    for rc, cnt in result.get("root_cause_distribution", {}).items():
        print(f"    {rc:<30s}: {cnt}")

    print("\n  Pipeline Stage Distribution:")
    for st, cnt in result.get("pipeline_stage_distribution", {}).items():
        print(f"    {st:<35s}: {cnt}")

    print("\n  Severity Distribution:")
    for sv, cnt in result.get("severity_distribution", {}).items():
        print(f"    {sv:<12s}: {cnt}")

    print("\n  Impact Distribution:")
    for il, cnt in result.get("impact_distribution", {}).items():
        print(f"    {il:<12s}: {cnt}")

    print("\n  Priority Fix List (Top 5):")
    for fix in result.get("priority_fixes", []):
        print(
            f"    Priority {fix['rank']}: {fix['fix_title']} "
            f"(score={fix['priority_score']}, "
            f"+{fix['expected_improvement_pct']}%)"
        )

    print("\n  Validation Rules:")
    for rule, passed in result.get("rule_results", {}).items():
        status = "PASS" if passed else "FAIL"
        print(f"    [{status}] {rule}")

    print("\n  Exported Artefacts:")
    for name, path in result.get("exported_paths", {}).items():
        print(f"    {name}")

    print("\n" + "=" * 72)
    print(f"Phase QA.1.1 complete — MODEL_VERSION {MODEL_VERSION}")
    print("=" * 72)


if __name__ == "__main__":
    main()
