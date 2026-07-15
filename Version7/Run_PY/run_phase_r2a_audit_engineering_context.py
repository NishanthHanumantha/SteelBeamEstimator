"""
run_phase_r2a_audit_engineering_context.py
Runner for Phase R.2A.AUDIT — READ-ONLY forensic audit
MODEL_VERSION: 7.5.2

Usage (from project root):
    python Version7/Run_PY/run_phase_r2a_audit_engineering_context.py
"""
import importlib.util
import pathlib
import sys
import types

SCRIPT_DIR    = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT  = SCRIPT_DIR.parent.parent
VERSION7_SRC  = PROJECT_ROOT / "Version7" / "src"
VERSION7_ROOT = PROJECT_ROOT / "Version7"

if str(VERSION7_SRC) not in sys.path:
    sys.path.insert(0, str(VERSION7_SRC))

_PKG_DIR = VERSION7_SRC / "PhaseR.2A.AUDIT_engineering_context"
pkg_name = "PhaseR2AAUDIT"

pkg_mod = types.ModuleType(pkg_name)
pkg_mod.__path__ = [str(_PKG_DIR)]
pkg_mod.__package__ = pkg_name
sys.modules[pkg_name] = pkg_mod


def _load_sub(name: str):
    s = importlib.util.spec_from_file_location(
        f"{pkg_name}.{name}", _PKG_DIR / f"{name}.py"
    )
    m = importlib.util.module_from_spec(s)
    m.__package__ = pkg_name
    sys.modules[f"{pkg_name}.{name}"] = m
    s.loader.exec_module(m)
    return m


for _sub in [
    "__init__",
    "dxf_forensic_auditor",
    "audit_validator",
    "audit_writer",
    "phase_r2a_audit_orchestrator",
]:
    _load_sub(_sub)

OUTPUT_DIR = (
    VERSION7_ROOT / "data" / "output" / "PhaseR.2A.AUDIT_engineering_context"
)
orch_mod = sys.modules[f"{pkg_name}.phase_r2a_audit_orchestrator"]
Orchestrator = orch_mod.PhaseR2AAuditOrchestrator

orchestrator = Orchestrator(v7_root=VERSION7_ROOT, output_dir=OUTPUT_DIR)
result = orchestrator.run()

print(f"\n  PHASE R.2A.AUDIT RESULT")
print(f"  Status           : {result.get('status')}")
print(f"  Validation       : {result.get('validation_score')}")
print(f"  Root cause       : {result.get('root_cause')}")
print(f"  Confidence       : {result.get('confidence_percent')}%")
print(f"  FY-550 in DXF    : {result.get('fy550_in_dxf')}")
print(f"  Artefacts        : {len(result.get('export_paths', {}))}")

sys.exit(0 if result.get("status") == "PASS" else 1)
