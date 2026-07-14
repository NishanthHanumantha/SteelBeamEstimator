"""
Runner — Phase L.2.1 Engineering Feature Extraction Engine
MODEL_VERSION : 6.4.1
PROJECT       : VERSION6

Usage:
    cd Version7
    python Run_PY/run_phase_l2_1_engineering_feature_extraction.py

Prerequisites:
    Phase L.2 must have been run first to produce BeamReinforcementModel output.
    python Run_PY/run_phase_l2_engineering_reinforcement_interpretation.py

This phase extracts engineering observations from every reinforcement bar.
It does NOT assign semantic roles. It does NOT modify BeamReinforcementModel.
"""

import sys
import os
from pathlib import Path

# ── Environment bootstrap ──────────────────────────────────────────────────
RUNNER_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = RUNNER_DIR.parent
SRC_PHASE = PROJECT_ROOT / "src" / "PhaseL.2.1 - engineering_feature_extraction"

for extra in [SRC_PHASE]:
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

os.chdir(PROJECT_ROOT)


def main() -> None:
    print("=" * 80)
    print("Phase L.2.1 - Engineering Feature Extraction Engine")
    print(f"MODEL_VERSION : 6.4.1")
    print(f"Project Root  : {PROJECT_ROOT}")
    print(f"Source Package: {SRC_PHASE.name}")
    print("=" * 80)

    from feature_engine import EngineeringFeatureExtractionEngine

    engine = EngineeringFeatureExtractionEngine(project_root=PROJECT_ROOT)
    result = engine.run()

    val = result.get("validation") or {}
    exp = result.get("export_validation") or {}
    stats = result.get("statistics") or {}

    print(f"\nValidation  : {val.get('status')}  "
          f"({val.get('summary', {}).get('passed', 0)}/{val.get('summary', {}).get('total_checks', 0)} passed)")
    print(f"Exports     : {exp.get('status')}  "
          f"({exp.get('summary', {}).get('passed', 0)}/{exp.get('summary', {}).get('total', 0)} passed)")
    print(f"Total Features   : {stats.get('total_features', 0)}")
    print(f"Total Beams      : {stats.get('total_beams', 0)}")
    print(f"Completeness     : {stats.get('completeness_rate_percent', 0)}%")

    zones = stats.get("zone_distribution") or {}
    if zones:
        print("\nPosition Zone Distribution:")
        for z, cnt in sorted(zones.items()):
            if cnt:
                print(f"  {z:<20}: {cnt}")

    if val.get("status") == "PASS" and exp.get("status") == "PASS":
        print("\n[COMPLETE] Phase L.2.1 - EngineeringFeatureModel ready.")
        print("           Future interpretation phases may consume these features")
        print("           instead of directly interpreting raw geometry.")
        sys.exit(0)
    else:
        failed_checks = [c for c in (val.get("checks") or []) if c.get("status") == "FAIL"]
        print("\n[ISSUES] Phase L.2.1 completed with validation issues:")
        for c in failed_checks:
            print(f"  FAIL: {c['name']} — {c.get('detail', '')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
