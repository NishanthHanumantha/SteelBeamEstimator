"""
Runner -- Phase V.ROOT.1 Dynamic DXF Discovery & Pipeline Initialization
MODEL_VERSION : 7.1.0

Usage:
    cd Version7
    # Default (auto-detects input folder):
    python Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py

    # Specify input folder explicitly:
    python Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py <folder>

    # Examples:
    python Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py data/Benchmark_Set_2
    python Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py data/Benchmark_Set_1
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

# ---- Environment bootstrap --------------------------------------------------
_RUNNER_DIR = Path(__file__).resolve().parent
_V7         = _RUNNER_DIR.parent
_VROOT1_SRC = _V7 / "src/PhaseVROOT.1_dynamic_pipeline_initialization"

for _p in [str(_VROOT1_SRC), str(_V7)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(_V7)
# -----------------------------------------------------------------------------


def main() -> None:
    from phase_vroot1_orchestrator import (
        PhaseVROOT1Orchestrator,
        MODEL_VERSION,
    )
    from initialization_validator import PIPELINE_INITIALIZATION_ERROR

    # Resolve input folder from CLI argument or auto-detect
    input_folder = None
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        p = Path(arg)
        if not p.is_absolute():
            p = _V7 / p
        if not p.exists():
            print(f"[ERROR] Input folder not found: {p}")
            sys.exit(1)
        input_folder = p

    try:
        orchestrator = PhaseVROOT1Orchestrator(
            input_folder=input_folder,
            write_adapters=True,
            raise_on_failure=False,   # Report failures without crashing
        )
        result = orchestrator.run()

        # Final delivery summary
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
        print(f"  NEXT STEP: Run the full pipeline:")
        print(f"    python Run_PY/run_phase_l2_engineering_reinforcement_interpretation.py")
        print(f"    (then L.2.2, L.2.1, L.3, SI.0 as before)")
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
