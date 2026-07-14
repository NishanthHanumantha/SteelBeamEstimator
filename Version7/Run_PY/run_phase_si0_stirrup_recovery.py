"""
Runner — Phase SI.0 Stirrup Recovery & Interpretation Engine
MODEL_VERSION: 6.6.2

Executes SI.0, then triggers SI.1 + V.B.1 to regenerate production output.

Usage:
    python run_phase_si0_stirrup_recovery.py
"""
import sys
import pathlib

_ROOT   = pathlib.Path(__file__).parents[2]
_SI0_SRC = _ROOT / "Version7" / "src" / "PhaseSI.0_stirrup_recovery"
_SI1_SRC = _ROOT / "Version7" / "src" / "PhaseSI.1_stirrup_improvement"
_VB1_SRC = _ROOT / "Version7" / "src" / "PhaseVB.1_production_output_completion"

for p in [str(_SI0_SRC), str(_SI1_SRC), str(_VB1_SRC)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from phase_si0_orchestrator import PhaseSI0Orchestrator

if __name__ == "__main__":
    # Step 1: SI.0 recovery
    si0 = PhaseSI0Orchestrator()
    result = si0.run()

    # Step 2: Re-run SI.1 pointing at the recovered model
    print("\nRunning Phase SI.1 with recovered stirrup model...")
    from phase_si1_orchestrator import PhaseSI1Orchestrator

    si0_out    = _ROOT / "Version7" / "data/output/PhaseSI.0_stirrup_recovery"
    recovered_l2 = si0_out / "beam_reinforcement_models.json"

    si1 = PhaseSI1Orchestrator(l2_path=recovered_l2)
    si1.run()

    # Step 3: Regenerate Estimation_Output.xlsx via V.B.1
    print("\nRegenerating Estimation_Output.xlsx via Phase V.B.1...")
    from phase_vb1_orchestrator import PhaseVB1Orchestrator

    vb1 = PhaseVB1Orchestrator(l2_path=recovered_l2)
    vb1_result = vb1.run()
    sys.exit(vb1_result.pipeline_exit_code)
