"""
Runner — Phase L.2.2 Engineering Geometry Recovery & Beam Coverage Validation.

Usage
-----
    python run_phase_l2_2_geometry_recovery.py

Sequence executed
-----------------
1.  Bootstrap Python path so all L.2.2 and L.2.1 modules are importable.
2.  Run PhaseL22Orchestrator which:
      a. Detects gap beams (in drawing but missing from L.2.1).
      b. Recovers EngineeringGeometry for each gap beam.
      c. Injects placeholder bars and writes extended beam models.
      d. Re-triggers Phase L.2.1 — all 18 beams now processed.
      e. Builds Coverage Matrix across all pipeline stages.
      f. Validates Pipeline Consistency (4 rules, fail-fast).
      g. Generates traceability map.
      h. Exports 6 output artefacts.
3.  Print execution summary.
"""

from __future__ import annotations

import sys
from pathlib import Path

# ── path bootstrap ────────────────────────────────────────────────────────────
_this = Path(__file__).resolve()
_version6 = _this.parent.parent                       # Version7/
_l22_src = _version6 / "src/PhaseL.2.2_geometry_recovery"
_l21_src = _version6 / "src/PhaseL.2.1 - engineering_feature_extraction"

for _p in [str(_l22_src), str(_l21_src), str(_version6)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── main ─────────────────────────────────────────────────────────────────────
from phase_l22_orchestrator import PhaseL22Orchestrator


def main() -> None:
    print("=" * 70)
    print("Phase L.2.2 — Engineering Geometry Recovery")
    print("          & Beam Coverage Validation Engine")
    print("MODEL_VERSION : 6.4.2")
    print("=" * 70)

    orchestrator = PhaseL22Orchestrator(project_root=_version6)
    result = orchestrator.run()

    # ── final summary ─────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("EXECUTION COMPLETE")
    print("=" * 70)

    rec = result.get("recovery_summary") or {}
    post = result.get("post_recovery") or {}
    cov = post.get("coverage") or {}
    cons = post.get("consistency") or {}
    exp = result.get("export_validation") or {}
    trace = result.get("traceability_summary") or {}

    print(f"  Run timestamp       : {result.get('run_timestamp', '?')}")
    print(f"  Duration            : {result.get('duration_s', 0):.2f}s")
    print()
    print("  RECOVERY")
    print(f"    Gap beams found   : {len(rec.get('gap_beam_ids', []))}")
    print(f"    Recovered         : {rec.get('recovered_count', '?')}")
    print(f"    Failed            : {rec.get('failed_count', '?')}")
    print()
    print("  COVERAGE")
    src = cov.get("source_counts") or {}
    print(f"    Detected beams    : {src.get('drawing_parser', '?')}")
    print(f"    Engineering objs  : {src.get('engineering_objects', '?')}")
    print(f"    Specifications    : {src.get('specifications', '?')}")
    print(f"    Geometry registry : {src.get('geometry_registry', '?')}")
    print(f"    Feature beams     : {src.get('engineering_features', '?')}")
    print(f"    Coverage %        : {cov.get('coverage_percent', '?')}%")
    print(f"    Beams PASS        : {cov.get('beams_pass', '?')}")
    print(f"    Beams FAIL        : {cov.get('beams_fail', '?')}")
    print()
    print("  PIPELINE VALIDATION")
    print(f"    Status            : {cons.get('pipeline_status', '?')}")
    counts = cons.get("counts") or {}
    print(f"    Detected Beams    : {counts.get('detected_beams', '?')}")
    print(f"    Engineering Objs  : {counts.get('engineering_objects', '?')}")
    print(f"    Specifications    : {counts.get('specifications', '?')}")
    print(f"    Geometry Objects  : {counts.get('geometry_objects', '?')}")
    print(f"    Feature Beams     : {counts.get('feature_beams', '?')}")
    print()
    print("  TRACEABILITY")
    print(f"    Original geometry : {trace.get('original_geometry_beams', '?')}")
    print(f"    Recovered geometry: {trace.get('recovered_geometry_beams', '?')}")
    print(f"    Coverage %        : {trace.get('coverage_percent', '?')}%")
    print()
    print("  EXPORT")
    print(f"    Status            : {exp.get('status', '?')}")
    for f in exp.get("files") or []:
        icon = "[OK]  " if f["status"] == "OK" else "[MISS]"
        print(f"    {icon} {f['file']}")
    print()

    status = cons.get("pipeline_status", "UNKNOWN")
    if status == "PASS":
        print("  RESULT: Phase L.2.2 PASSED — all beams covered, pipeline consistent.")
    else:
        print("  RESULT: Phase L.2.2 completed with warnings — check failed rules above.")
    print("=" * 70)


if __name__ == "__main__":
    main()
