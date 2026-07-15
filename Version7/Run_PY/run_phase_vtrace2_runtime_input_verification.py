"""
Runner — Phase V.TRACE.2 Runtime Input Verification
MODEL_VERSION : 7.1.3
PROJECT       : VERSION7
Type          : Read-Only Runtime Diagnostics

Usage:
    cd Version7
    python Run_PY/run_phase_vtrace2_runtime_input_verification.py

IMPORTANT:
  This phase is DIAGNOSTIC ONLY.
  No engineering logic is modified.
  No pipeline outputs are regenerated.
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
_ROOT    = pathlib.Path(__file__).parent.parent   # Version7/
_PKG_DIR = _ROOT / "src" / "PhaseVTRACE.2_runtime_input_verification"
_L2_DIR  = _ROOT / "src" / "PhaseL.2 - engineering_reinforcement_interpretation"

for _p in [str(_ROOT / "src"), str(_L2_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Module loader (mirrors V.TRACE.1 pattern) ─────────────────────────────────
PKG_NAME = "PhaseVTRACE2"


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

# Register all sub-modules so relative imports resolve
_SUB_MODULES = [
    "runtime_models",
    "runtime_path_scanner",
    "runtime_file_loader",
    "runtime_beam_counter",
    "runtime_adapter_verifier",
    "runtime_version_detector",
    "runtime_dependency_detector",
    "runtime_filter_detector",
    "runtime_cache_detector",
    "runtime_statistics",
    "runtime_reporter",
    "runtime_export",
]
for _sub in _SUB_MODULES:
    _load_mod(f"{PKG_NAME}.{_sub}", _PKG_DIR / f"{_sub}.py")

_orch_mod = _load_mod(f"{PKG_NAME}.phase_vtrace2_orchestrator",
                      _PKG_DIR / "phase_vtrace2_orchestrator.py")


def main() -> int:
    print("=" * 70)
    print("Phase V.TRACE.2 -- Runtime Input Verification")
    print("MODEL_VERSION : 7.1.3")
    print("Type          : Read-Only Runtime Diagnostics")
    print(f"Project Root  : {_ROOT}")
    print("=" * 70)

    orchestrator = _orch_mod.PhaseVTRACE2Orchestrator()
    result       = orchestrator.run()

    validation = result.get("validation") or []
    stats      = result.get("statistics") or {}
    exported   = result.get("exported") or {}
    report     = result.get("report") or {}

    passed = sum(1 for v in validation if v.get("status") == "PASS")
    failed = sum(1 for v in validation if v.get("status") == "FAIL")

    print(f"\nValidation    : {passed}/{len(validation)} PASS")
    print(f"Files loaded  : {stats.get('files_loaded', 0)}/{stats.get('files_total', 0)}")
    print(f"Input beams   : {stats.get('input_beam_count', 0)}")
    print(f"Output beams  : {stats.get('output_beam_count', 0)}")
    print(f"Stale files   : {stats.get('stale_files', 0)} (stages: {stats.get('stale_stages', [])})")
    print(f"Exports       : {len(exported)} artefacts")

    root_cause = report.get("sections", {}).get("11_root_cause", "")
    recom      = report.get("sections", {}).get("12_engineering_recommendation", "")
    print(f"\n[ROOT CAUSE]\n{root_cause}")
    print(f"\n[RECOMMENDATION]\n{recom}")

    print(f"\n[VALIDATION RULES]")
    for v in validation:
        mark = "[PASS]" if v.get("status") == "PASS" else "[FAIL]"
        print(f"  {mark} {v.get('rule_id')}: {v.get('name')} -- {str(v.get('detail',''))[:80]}")

    overall = "PASS" if failed == 0 else "FAIL"
    print(f"\n[{overall}] Phase V.TRACE.2 complete.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
