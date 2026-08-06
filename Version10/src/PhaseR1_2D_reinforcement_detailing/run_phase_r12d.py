"""Package-local alias for run_phase_r12d (see Run_PY runner)."""
from phase_r12d_orchestrator import PhaseR12DOrchestrator

if __name__ == "__main__":
    raise SystemExit(0 if PhaseR12DOrchestrator().run().get("status") in ("PASS", "WARN") else 1)
