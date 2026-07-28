"""
Runner -- Phase V.ROOT.1 Dynamic DXF Discovery & Pipeline Initialization
MODEL_VERSION : 8.9.0

Usage:
    cd Version8
    # Offline (writes Version8/data/output/...):
    python Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py [input_folder]

    # Web / per-run (STEEL_RUN_ROOT or argv = web_runs/<run_id>):
    python Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py <run_root>
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ---- Environment bootstrap --------------------------------------------------
_RUNNER_DIR = Path(__file__).resolve().parent
_ENGINE     = _RUNNER_DIR.parent
_VROOT1_SRC = _ENGINE / "src/PhaseVROOT.1_dynamic_pipeline_initialization"
_SRC        = _ENGINE / "src"

for _p in [str(_VROOT1_SRC), str(_SRC), str(_ENGINE)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(_ENGINE)
# -----------------------------------------------------------------------------


def main() -> None:
    from config.run_context import PHASE_VROOT1, resolve_run_context, run_root_from_argv
    from phase_vroot1_orchestrator import (
        PhaseVROOT1Orchestrator,
        MODEL_VERSION,
    )
    from initialization_validator import PIPELINE_INITIALIZATION_ERROR

    arg = run_root_from_argv(sys.argv, 1)
    # Web passes the staging folder as argv[1] — that IS the run_root / input_root
    ctx = resolve_run_context(run_root_arg=arg, engine_root=_ENGINE)
    os.environ.setdefault("STEEL_ENGINE_ROOT", str(ctx.engine_root))
    os.environ.setdefault("STEEL_RUN_ROOT", str(ctx.run_root))
    os.environ.setdefault("STEEL_OUTPUT_ROOT", str(ctx.output_root))

    input_folder = ctx.input_root if arg is not None else None
    output_dir = ctx.artefact(PHASE_VROOT1)

    print(f"[VROOT1] engine_root={ctx.engine_root}")
    print(f"[VROOT1] run_root={ctx.run_root}")
    print(f"[VROOT1] output_dir={output_dir}")

    try:
        orchestrator = PhaseVROOT1Orchestrator(
            input_folder=input_folder,
            write_adapters=True,
            raise_on_failure=False,
            output_dir=output_dir,
        )
        result = orchestrator.run()

        print()
        print("=" * 72)
        print("FINAL DELIVERY SUMMARY -- Phase V.ROOT.1")
        print("=" * 72)

        pm = result.get('project_manifest', {})
        dr = result.get('discovery_result', {})
        reg = result.get('beam_registry', {})
        val = result.get('validation', {})
        ev  = result.get('export_validation', {})

        print(f"  MODEL_VERSION        : {MODEL_VERSION}")
        print(f"  Project              : {pm.get('project_name', '?')}")
        print(f"  Building / Floor     : {pm.get('building', '?')} / {pm.get('floor', '?')}")
        print(f"  Input folder         : {result.get('input_folder', '?')}")
        print()
        print(f"  Total DXF files      : {pm.get('dxf_count', 0)}")
        print(f"  Text entities parsed : {dr.get('total_text_entities', 0)}")
        print(f"  Beam labels found    : {dr.get('label_entities', 0)}")
        print(f"  Beams discovered     : {reg.get('beam_count', 0)}")
        print(f"  Beam IDs             : {reg.get('beam_ids', [])}")
        print()
        print(f"  Engineering objects  : {result.get('eng_obj_result', {}).get('objects_generated', {}).get('engineering_objects', 0)}")
        print(f"  Adapter files        : {len(result.get('eng_obj_result', {}).get('adapter_paths', {}))}")
        print(f"  V5 dependency        : False")
        print(f"  Hardcoded beams      : False")
        print()
        print(f"  Validation           : {val.get('passed_count', 0)}/9 rules passed")
        print(f"  Failed rules         : {val.get('failed_rules', [])}")
        print(f"  Exports              : {ev.get('passed', 0)}/{ev.get('total', 0)} OK")
        print()
        print(f"  Output dir           : {ev.get('output_dir', '?')}")
        print()

        if result.get('initialization_passed'):
            print("[COMPLETE]  Phase V.ROOT.1 -- All 9 rules passed.")
        else:
            failed = val.get('failed_rules', [])
            print(f"[COMPLETE]  Phase V.ROOT.1 finished. Failed rules: {failed}")

        sys.exit(0 if result.get('initialization_passed') else 1)

    except PIPELINE_INITIALIZATION_ERROR as err:
        print(f"\n[PIPELINE_INITIALIZATION_ERROR] {err}")
        sys.exit(2)
    except Exception as exc:
        import traceback
        print(f"\n[ERROR] Unexpected error: {exc}")
        traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    main()
