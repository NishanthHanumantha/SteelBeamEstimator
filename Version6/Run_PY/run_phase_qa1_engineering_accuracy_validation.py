"""
Phase QA.1 — Engineering Accuracy Benchmark & Validation Framework
Runner script — MODEL_VERSION: 6.5.1

Usage:
    python Version6/Run_PY/run_phase_qa1_engineering_accuracy_validation.py
    python Version6/Run_PY/run_phase_qa1_engineering_accuracy_validation.py --gt path/to/gt.json
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import traceback

# ── Bootstrap sys.path ────────────────────────────────────────────────────
_this = pathlib.Path(__file__).resolve()
_version6 = _this.parent.parent                              # Version6/
_qa1_src  = _version6 / "src" / "PhaseQA.1_engineering_accuracy_validation"

for _p in [str(_qa1_src), str(_version6)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from phase_qa1_orchestrator import PhaseQA1Orchestrator  # noqa: E402


def main() -> None:
    _workspace = _version6.parent  # SteelBeamEstimator/

    parser = argparse.ArgumentParser(
        description="Phase QA.1 — Engineering Accuracy Benchmark & Validation Framework"
    )
    parser.add_argument(
        "--gt",
        default=str(_workspace / "Version6" / "data" / "benchmarks" / "benchmark_drawing_1.json"),
        help="Path to ground truth benchmark JSON file (default: benchmark_drawing_1.json)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(_workspace / "Version6" / "data" / "output" / "PhaseQA.1_engineering_accuracy_validation"),
        help="Output directory for benchmark artefacts",
    )
    args = parser.parse_args()

    print("=" * 72)
    print("  Phase QA.1 — Engineering Accuracy Benchmark & Validation")
    print("  MODEL_VERSION: 6.5.1")
    print("=" * 72)
    print(f"  Ground Truth : {args.gt}")
    print(f"  Output Dir   : {args.output_dir}")
    print("=" * 72)
    print()

    try:
        orchestrator = PhaseQA1Orchestrator(
            ground_truth_path=args.gt,
            output_dir=args.output_dir,
        )
        result = orchestrator.run()

        print()
        print("=" * 72)
        print("  BENCHMARK RESULTS SUMMARY")
        print("=" * 72)
        print(f"  Drawing              : {result.drawing_name}")
        print(f"  Benchmark ID         : {result.benchmark_id}")
        print(f"  Model Version        : {result.model_version}")
        print()
        print("  KPI RESULTS:")
        kpis = [
            ("Beam Detection",    result.beam_detection_accuracy),
            ("Beam Assignment",   result.beam_assignment_accuracy),
            ("Geometry",          result.geometry_accuracy),
            ("Feature Extraction",result.feature_accuracy),
            ("Top/Bottom",        result.top_bottom_accuracy),
            ("Diameter",          result.diameter_accuracy),
            ("Quantity",          result.quantity_accuracy),
            ("Pattern",           result.pattern_accuracy),
            ("BBS",               result.bbs_accuracy),
            ("Steel Weight",      result.steel_weight_accuracy),
            ("Cut Length",        result.cut_length_accuracy),
        ]
        for name, val in kpis:
            v = f"{val:.4f}%" if val is not None else "NOT AVAILABLE"
            print(f"    {name:<22} : {v}")
        print()
        print(f"  Overall Engineering  : {result.overall_engineering_accuracy}%")
        print(f"  Weighted Score       : {result.weighted_score}/100")
        print(f"  Classification       : {result.classification}")
        print(f"  Pass/Fail            : {result.pass_fail}")
        rules_status = "PASSED" if result.validation_passed else "FAILED"
        print(f"  Validation Rules     : {rules_status}")
        print(f"  Error Count          : {len(result.error_summary)}")
        print()
        print("  [COMPLETE] Phase QA.1 benchmark validation complete.")
        print("=" * 72)

    except Exception as exc:
        print(f"\n[ISSUES] Phase QA.1 failed: {exc}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
