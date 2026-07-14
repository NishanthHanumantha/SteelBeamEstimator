"""
Runner — Phase SI.1 Stirrup Improvement Engine
MODEL_VERSION: 6.6.1

Runs the stirrup improvement engine independently, then regenerates
Estimation_Output.xlsx via Phase V.B.1.

Usage:
    python run_phase_si1_stirrup_improvement.py
"""
import sys
import pathlib

_ROOT = pathlib.Path(__file__).parents[2]
_SI1_SRC = _ROOT / "Version7" / "src" / "PhaseSI.1_stirrup_improvement"
_VB1_SRC = _ROOT / "Version7" / "src" / "PhaseVB.1_production_output_completion"

for p in [str(_SI1_SRC), str(_VB1_SRC)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from phase_si1_orchestrator import PhaseSI1Orchestrator, STIRRUP_ENGINE_ERROR

if __name__ == "__main__":
    try:
        # Step 1: Run SI.1 engine
        orch = PhaseSI1Orchestrator()
        result = orch.run()

        # Step 2: Regenerate Estimation_Output.xlsx with improved stirrups
        print("\nRegenerating Estimation_Output.xlsx via Phase V.B.1...")
        from phase_vb1_orchestrator import PhaseVB1Orchestrator
        vb1 = PhaseVB1Orchestrator()
        vb1_result = vb1.run()
        sys.exit(vb1_result.pipeline_exit_code)

    except STIRRUP_ENGINE_ERROR as e:
        print(f"\nSTIRRUP_ENGINE_ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nFATAL: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
