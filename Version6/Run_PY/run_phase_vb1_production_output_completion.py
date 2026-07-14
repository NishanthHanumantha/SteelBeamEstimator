"""
Runner — Phase V.B.1 Production Output Completion
MODEL_VERSION: 6.6.0

Usage:
    python run_phase_vb1_production_output_completion.py
"""
import sys
import pathlib

_ROOT = pathlib.Path(__file__).parents[2]
_SRC  = _ROOT / "Version6" / "src" / "PhaseVB.1_production_output_completion"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from phase_vb1_orchestrator import PhaseVB1Orchestrator, PRODUCTION_OUTPUT_ERROR

if __name__ == "__main__":
    try:
        orch = PhaseVB1Orchestrator()
        result = orch.run()
        sys.exit(result.pipeline_exit_code)
    except PRODUCTION_OUTPUT_ERROR as e:
        print(f"\nPRODUCTION_OUTPUT_ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nFATAL: {e}", file=sys.stderr)
        sys.exit(1)
