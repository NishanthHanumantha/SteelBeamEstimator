"""
Runner — Phase V.RUN.1 Full Pipeline Re-execution (Benchmark Set 2)
MODEL_VERSION : 7.2.0
PROJECT       : VERSION7
Type          : Production Pipeline Execution & Fresh Artefact Regeneration

Usage:
    cd Version8
    python Run_PY/run_phase_vrun1_pipeline_reexecution.py

Executes V.ROOT.1 → L.2 → SI.0 → SI.1 → L.2.2 → L.2.1 → L.3 → V.B.1
in strict sequential order.

NO engineering modifications. Clean production rebuild.
"""

import sys
import io
import importlib.util
import types
import pathlib

# ── UTF-8 safe output ─────────────────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Path bootstrap ─────────────────────────────────────────────────────────────
_ROOT    = pathlib.Path(__file__).parent.parent   # Version8/
_PKG_DIR = _ROOT / "src" / "PhaseVRUN.1_pipeline_reexecution"

if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

# ── Module loader (mirrors V.TRACE pattern) ────────────────────────────────────
PKG_NAME = "PhaseVRUN1"


def _load_mod(name: str, filepath: pathlib.Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        name, str(filepath),
        submodule_search_locations=[str(_PKG_DIR)],
    )
    m = importlib.util.module_from_spec(spec)
    m.__package__ = PKG_NAME
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


# Register package __init__
_init_spec = importlib.util.spec_from_file_location(
    PKG_NAME, str(_PKG_DIR / "__init__.py"),
    submodule_search_locations=[str(_PKG_DIR)],
)
_pkg_mod = importlib.util.module_from_spec(_init_spec)
_pkg_mod.__package__ = PKG_NAME
sys.modules[PKG_NAME] = _pkg_mod
_init_spec.loader.exec_module(_pkg_mod)

# Register all sub-modules
_SUB_MODULES = [
    "pipeline_execution_models",
    "stale_output_cleaner",
    "pipeline_runner",
    "stage_execution_monitor",
    "artefact_freshness_validator",
    "beam_count_monitor",
    "execution_statistics",
    "execution_reporter",
    "execution_export",
]
for _sub in _SUB_MODULES:
    _load_mod(f"{PKG_NAME}.{_sub}", _PKG_DIR / f"{_sub}.py")

_orch_mod = _load_mod(f"{PKG_NAME}.phase_vrun1_orchestrator",
                      _PKG_DIR / "phase_vrun1_orchestrator.py")


def main() -> int:
    print("=" * 70)
    print("Phase V.RUN.1 -- Full Pipeline Re-execution (Benchmark Set 2)")
    print("MODEL_VERSION : 7.2.0")
    print(f"Project Root  : {_ROOT}")
    print("=" * 70)

    orchestrator = _orch_mod.PhaseVRUN1Orchestrator()
    result       = orchestrator.run()

    stages      = result.get("stage_results") or []
    validation  = result.get("validation") or []
    statistics  = result.get("statistics") or {}
    exported    = result.get("exported") or {}
    report      = result.get("report") or {}
    propagation = result.get("propagation") or []
    wb          = result.get("workbook_path")

    passed_v = sum(1 for v in validation if v.get("status") == "PASS")
    failed_v = sum(1 for v in validation if v.get("status") == "FAIL")
    passed_s = sum(1 for s in stages if s.status == "SUCCESS")

    print(f"\n{'=' * 70}")
    print(f"PIPELINE SUMMARY")
    print(f"  Stages:        {passed_s}/{len(stages)} SUCCESS")
    print(f"  Validation:    {passed_v}/{len(validation)} PASS")
    print(f"  Duration:      {statistics.get('total_duration_s', 0)}s")
    print(f"  Initial beams: {statistics.get('initial_beam_count', 0)}")
    print(f"  Final beams:   {statistics.get('final_beam_count', 0)}")
    print(f"  Exports:       {len(exported)} artefacts")
    print(f"  Workbook:      {wb or 'NOT FOUND'}")

    print(f"\nBEAM PROPAGATION")
    for row in propagation:
        delta_str = f"  [delta {row.get('delta', 0):+d}]" if row.get("delta") else ""
        print(f"  {row['stage_id']:<8}  {row['beam_count']:>3} beams{delta_str}")

    print(f"\nVALIDATION RULES")
    for v in validation:
        mark = "[PASS]" if v.get("status") == "PASS" else "[FAIL]"
        print(f"  {mark} {v.get('rule_id')}: {v.get('name')} -- {str(v.get('detail',''))[:80]}")

    overall = result.get("overall_status", "UNKNOWN")
    print(f"\n[{overall}] Phase V.RUN.1 complete.")
    return 0 if failed_v == 0 and passed_s == len(stages) else 1


if __name__ == "__main__":
    sys.exit(main())
