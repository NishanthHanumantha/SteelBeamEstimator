"""
run_phase_vtrace1_pipeline_traceability.py
Runner script for Phase V.TRACE.1 — End-to-End Pipeline Traceability Audit.
MODEL_VERSION: 7.1.2
"""

import sys
import io
import importlib
import pathlib

# Force UTF-8 output on Windows (avoids cp1252 UnicodeEncodeError)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Bootstrap Version7 src path
_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "src"))

# Package folder is 'PhaseVTRACE.1_pipeline_traceability' (dot in name),
# so we must use importlib with the filesystem name.
_pkg_dir = _ROOT / "src" / "PhaseVTRACE.1_pipeline_traceability"
spec = importlib.util.spec_from_file_location(
    "phase_vtrace1_orchestrator",
    str(_pkg_dir / "phase_vtrace1_orchestrator.py"),
    submodule_search_locations=[str(_pkg_dir)],
)
orchestrator_mod = importlib.util.module_from_spec(spec)

# Pre-register all sub-modules with the same package prefix so internal
# relative imports resolve correctly.
import importlib.util, types

PKG_NAME = "PhaseVTRACE1"

def _load_module(name: str, filepath: pathlib.Path, pkg=None) -> types.ModuleType:
    sp = importlib.util.spec_from_file_location(
        name, str(filepath),
        submodule_search_locations=[str(_pkg_dir)],
    )
    m = importlib.util.module_from_spec(sp)
    m.__package__ = PKG_NAME
    sys.modules[name] = m
    sp.loader.exec_module(m)
    return m

_sub_modules = [
    "engineering_trace_models",
    "stage_snapshot_collector",
    "beam_identity_tracker",
    "stage_comparator",
    "lifecycle_tracker",
    "beam_loss_detector",
    "duplication_detector",
    "pipeline_flow_analyzer",
    "root_cause_locator",
    "trace_validator",
    "trace_statistics",
    "trace_reporter",
    "trace_export",
]

# Register package init
init_spec = importlib.util.spec_from_file_location(
    PKG_NAME, str(_pkg_dir / "__init__.py"),
    submodule_search_locations=[str(_pkg_dir)],
)
pkg_mod = importlib.util.module_from_spec(init_spec)
pkg_mod.__package__ = PKG_NAME
sys.modules[PKG_NAME] = pkg_mod
init_spec.loader.exec_module(pkg_mod)

for sub in _sub_modules:
    _load_module(f"{PKG_NAME}.{sub}", _pkg_dir / f"{sub}.py")

orch_spec = importlib.util.spec_from_file_location(
    f"{PKG_NAME}.phase_vtrace1_orchestrator",
    str(_pkg_dir / "phase_vtrace1_orchestrator.py"),
    submodule_search_locations=[str(_pkg_dir)],
)
orch_mod = importlib.util.module_from_spec(orch_spec)
orch_mod.__package__ = PKG_NAME
sys.modules[f"{PKG_NAME}.phase_vtrace1_orchestrator"] = orch_mod
orch_spec.loader.exec_module(orch_mod)

if __name__ == "__main__":
    sys.exit(orch_mod.run())
