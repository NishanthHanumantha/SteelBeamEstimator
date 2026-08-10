"""
Run existing Phase VB.1 Excel generation against a sandbox run_root.
MODEL_VERSION: 10.5.6
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path
from typing import Any, Dict


def _bootstrap_vb1(engine_root: Path) -> None:
    pkg_dir = engine_root / "src" / "PhaseVB.1_production_output_completion"
    alias = "PhaseVB1"
    src = engine_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    if str(pkg_dir) not in sys.path:
        sys.path.insert(0, str(pkg_dir))

    if alias not in sys.modules:
        virtual_pkg = types.ModuleType(alias)
        virtual_pkg.__path__ = [str(pkg_dir)]
        virtual_pkg.__package__ = alias
        sys.modules[alias] = virtual_pkg

    for py_file in sorted(pkg_dir.glob("*.py")):
        mod_name = py_file.stem
        full_name = alias if mod_name == "__init__" else f"{alias}.{mod_name}"
        if full_name in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(full_name, str(py_file))
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        module.__package__ = alias
        sys.modules[full_name] = module
        spec.loader.exec_module(module)


def run_vb1_excel(
    *,
    engine_root: Path,
    sandbox_run_root: Path,
) -> Dict[str, Any]:
    """
    Generate Estimation_Output.xlsx via existing VB1 orchestrator.
    Inputs: R1.3 models under sandbox. Ownership is placed for provenance but
    is not consumed by VB1 (existing architecture).
    """
    engine_root = Path(engine_root)
    sandbox_run_root = Path(sandbox_run_root)
    _bootstrap_vb1(engine_root)

    from PhaseVB1.phase_vb1_orchestrator import PhaseVB1Orchestrator

    l2_path = (
        sandbox_run_root
        / "data"
        / "output"
        / "PhaseR1.3_pipeline_integration"
        / "beam_reinforcement_models_production.json"
    )
    output_dir = sandbox_run_root / "data" / "output" / "Production_Output"
    output_dir.mkdir(parents=True, exist_ok=True)

    os.environ["STEEL_ENGINE_ROOT"] = str(engine_root)
    os.environ["STEEL_RUN_ROOT"] = str(sandbox_run_root)
    os.environ["STEEL_OUTPUT_ROOT"] = str(sandbox_run_root / "data" / "output")

    orch = PhaseVB1Orchestrator(
        output_dir=output_dir,
        l2_path=l2_path,
        v7_root=engine_root,
        run_root=sandbox_run_root,
        use_r13_integration=False,
        use_r14_validation=False,
    )
    result = orch.run()
    xlsx = output_dir / "Estimation_Output.xlsx"
    return {
        "success": xlsx.exists(),
        "workbook_path": str(xlsx) if xlsx.exists() else None,
        "steel_weight_kg": getattr(result, "steel_weight_kg", None),
        "pipeline_exit_code": getattr(result, "pipeline_exit_code", None),
        "output_dir": str(output_dir),
        "r13_models": str(l2_path),
        "consumes_beam_ownership": False,
        "note": (
            "Existing VB1 reads R1.3 beam_reinforcement_models_production.json only; "
            "BeamOwnership is not an input to Excel generation."
        ),
    }
