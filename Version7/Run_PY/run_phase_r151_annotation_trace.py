"""
run_phase_r151_annotation_trace.py
Runner for Phase R.1.5.1 — Annotation Trace Forensic Audit
MODEL_VERSION: 7.8.2 — READ-ONLY

Usage (from project root):
    python Version7/Run_PY/run_phase_r151_annotation_trace.py
"""
import importlib.util
import pathlib
import sys
import types

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
VERSION7_SRC = PROJECT_ROOT / "Version7" / "src"
VERSION7_ROOT = PROJECT_ROOT / "Version7"

if str(VERSION7_SRC) not in sys.path:
    sys.path.insert(0, str(VERSION7_SRC))

_PKG_DIR = VERSION7_SRC / "PhaseR1.5.1_annotation_trace_audit"
pkg_name = "PhaseR151"

pkg_mod = types.ModuleType(pkg_name)
pkg_mod.__path__ = [str(_PKG_DIR)]
pkg_mod.__package__ = pkg_name
sys.modules[pkg_name] = pkg_mod

MODULES = [
    "__init__", "annotation_trace_models", "dxf_forensic_scanner",
    "annotation_inventory", "annotation_trace_builder", "annotation_group_trace",
    "engineering_bar_trace", "steel_trace", "bbs_trace", "diameter_trace",
    "beam_trace", "annotation_loss_detector", "annotation_statistics",
    "annotation_validator", "annotation_reporter", "annotation_export",
    "phase_r151_orchestrator",
]


def _load_sub(name: str):
    s = importlib.util.spec_from_file_location(
        f"{pkg_name}.{name}", _PKG_DIR / f"{name}.py"
    )
    m = importlib.util.module_from_spec(s)
    m.__package__ = pkg_name
    sys.modules[f"{pkg_name}.{name}"] = m
    s.loader.exec_module(m)
    return m


for _sub in MODULES:
    _load_sub(_sub)

OUTPUT_DIR = VERSION7_ROOT / "data" / "output" / "PhaseR1.5.1_annotation_trace_audit"
orch_mod = sys.modules[f"{pkg_name}.phase_r151_orchestrator"]
Orchestrator = orch_mod.PhaseR151Orchestrator

result = Orchestrator(v7_root=VERSION7_ROOT, output_dir=OUTPUT_DIR).run()

print(f"\n  PHASE R.1.5.1 RESULT")
print(f"  Status           : {result.get('status')}")
print(f"  Validation       : {result.get('validation', {}).get('score')}")
print(f"  Y10 conclusion   : {result.get('y10_audit', {}).get('conclusion', '')[:80]}")
print(f"  Artefacts        : {len(result.get('export_paths', {}))}")

sys.exit(0 if result.get("status") == "PASS" else 1)
