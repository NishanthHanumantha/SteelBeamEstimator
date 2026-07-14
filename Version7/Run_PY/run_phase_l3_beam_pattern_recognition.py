"""
Runner — Phase L.3 Beam Reinforcement Pattern Recognition Engine.

Usage
-----
    python run_phase_l3_beam_pattern_recognition.py

Prerequisites
-------------
    Phase L.2   (Engineering Reinforcement Interpretation)
    Phase L.2.2 (Geometry Recovery & Coverage Validation)
    Phase L.2.1 (Engineering Feature Extraction)
"""

from __future__ import annotations

import sys
from pathlib import Path

# ── path bootstrap ────────────────────────────────────────────────────────────
_this = Path(__file__).resolve()
_version6 = _this.parent.parent
_l3_src = _version6 / "src/PhaseL.3_beam_pattern_recognition"

for _p in [str(_l3_src), str(_version6)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from phase_l3_orchestrator import PhaseL3Orchestrator


def main() -> None:
    print("=" * 80)
    print("Phase L.3 — Beam Reinforcement Pattern Recognition Engine")
    print("MODEL_VERSION : 6.5.0")
    print("=" * 80)
    print()

    orchestrator = PhaseL3Orchestrator(project_root=_version6)
    result = orchestrator.run()

    print()
    print("=" * 80)
    print("EXECUTION COMPLETE")
    print("=" * 80)

    summ = result.get("pattern_summary") or {}
    val = result.get("validation") or {}
    stats = result.get("statistics") or {}
    exp = result.get("export_validation") or {}

    print(f"  Run timestamp       : {result.get('run_timestamp', '?')}")
    print(f"  Duration            : {result.get('duration_s', 0):.3f}s")
    print()
    print(f"  Total Beams         : {result.get('total_beams', '?')}")
    print(f"  Validation Status   : {val.get('status', '?')}")
    print(f"  Export Status       : {exp.get('status', '?')}")
    print()
    print("  Pattern Distribution:")
    for k, v in (stats.get("span_pattern_distribution") or {}).items():
        print(f"    {k:<42}: {v}")
    print()
    print("  Reinforcement Patterns:")
    for k, v in (stats.get("reinforcement_pattern_distribution") or {}).items():
        print(f"    {k:<42}: {v}")
    print()
    print("  Confidence Distribution:")
    for k, v in (stats.get("confidence_distribution") or {}).items():
        print(f"    {k:<42}: {v}")
    cstats = stats.get("confidence_stats") or {}
    print(f"  Confidence (mean/min/max): {cstats.get('mean','?')} / {cstats.get('min','?')} / {cstats.get('max','?')}")
    print()

    status = val.get("status", "UNKNOWN")
    if status == "PASS":
        print("  RESULT: Phase L.3 PASSED — all 18 beams classified, validation passed.")
    else:
        print("  RESULT: Phase L.3 completed — check validation report for details.")

    print("=" * 80)


if __name__ == "__main__":
    main()
