"""
Runner — Phase L.2 Engineering Reinforcement Interpretation Engine
MODEL_VERSION : 6.4.0
PROJECT       : VERSION6

Usage:
    cd Version6
    python Run_PY/run_phase_l2_engineering_reinforcement_interpretation.py
"""

import sys
import os
from pathlib import Path

# ── Environment bootstrap ──────────────────────────────────────────────────
RUNNER_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = RUNNER_DIR.parent
SRC_PHASE = PROJECT_ROOT / "src" / "PhaseL.2 - engineering_reinforcement_interpretation"

for extra in [SRC_PHASE]:
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

os.chdir(PROJECT_ROOT)


def main() -> None:
    print("=" * 80)
    print("Phase L.2 — Engineering Reinforcement Interpretation Engine")
    print(f"MODEL_VERSION : 6.4.0")
    print(f"Project Root  : {PROJECT_ROOT}")
    print(f"Source Package: {SRC_PHASE.name}")
    print("=" * 80)

    from interpretation_engine import EngineeringReinforcementInterpretationEngine

    engine = EngineeringReinforcementInterpretationEngine(project_root=PROJECT_ROOT)
    result = engine.run()

    val = result.get("validation") or {}
    exp = result.get("export_validation") or {}
    stats = result.get("statistics") or {}

    print(f"\nValidation  : {val.get('status')}  "
          f"({val.get('summary', {}).get('passed', 0)}/{val.get('summary', {}).get('total_checks', 0)} passed)")
    print(f"Exports     : {exp.get('status')}  "
          f"({exp.get('summary', {}).get('passed', 0)}/{exp.get('summary', {}).get('total', 0)} passed)")
    print(f"Beams       : {stats.get('total_beams', 0)}")
    print(f"Total Bars  : {stats.get('total_bars', 0)}")
    print(f"Class. Rate : {stats.get('classification_rate_percent', 0)}%")

    roles = stats.get("roles_distribution") or {}
    benchmark_roles = ["TOP_MAIN", "BOTTOM_MAIN", "TOP_EXTRA", "BOTTOM_EXTRA",
                       "STIRRUP", "SIDE_FACE_REINFORCEMENT", "SPACER_BAR"]
    print("\nRole Distribution:")
    for role in benchmark_roles:
        cnt = roles.get(role, 0)
        if cnt:
            print(f"  {role:<30} : {cnt}")

    if val.get("status") == "PASS" and exp.get("status") == "PASS":
        print("\n[COMPLETE] Phase L.2 — BeamReinforcementModel ready for downstream consumption.")
        sys.exit(0)
    else:
        failed_checks = [c for c in (val.get("checks") or []) if c.get("status") == "FAIL"]
        print("\n[ISSUES] Phase L.2 completed with validation issues:")
        for c in failed_checks:
            print(f"  FAIL: {c['name']} — {c.get('detail', '')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
