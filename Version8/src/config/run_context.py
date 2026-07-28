"""
Run context for web / offline pipeline execution (Phase D.5.1–D.5.3).

MODEL_VERSION: 8.9.2

Every production stage should resolve paths through RunContext instead of
hardcoding Version8/data/output or Benchmark_Set_* folders.

Web contract (set by webapp for every stage subprocess):
  STEEL_ENGINE_ROOT  → absolute path to Version8/
  STEEL_RUN_ROOT     → absolute path to Version8/data/web_runs/<run_id>/
  STEEL_OUTPUT_ROOT  → STEEL_RUN_ROOT/data/output

Offline CLI (no STEEL_RUN_ROOT):
  run_root = engine_root  → outputs remain Version8/data/output/...
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

PathLike = Union[str, Path]

# Standard phase output directory names (keep long names — engineering contract)
PHASE_VROOT1 = "PhaseVROOT.1_dynamic_pipeline_initialization"
PHASE_R1 = "PhaseR.1_generalized_reinforcement_discovery"
PHASE_R2A = "PhaseR.2A_engineering_context"
PHASE_R21B = "PhaseR2.1B_engineering_semantic_interpreter"
PHASE_R21C = "PhaseR2.1C_engineering_fact_normalization"
PHASE_R21D = "PhaseR2.1D_evidence_hypothesis_engine"
PHASE_L22 = "PhaseL.2.2_geometry_recovery"


@dataclass(frozen=True)
class RunContext:
    """Isolated run paths for one estimation."""

    engine_root: Path
    run_root: Path
    input_root: Path
    output_root: Path

    def artefact(self, *parts: str) -> Path:
        """Join under output_root (e.g. artefact(PHASE_R1, 'reinforcement_annotations.json'))."""
        return self.output_root.joinpath(*parts)

    def ensure_output_dirs(self) -> None:
        self.output_root.mkdir(parents=True, exist_ok=True)


def default_engine_root() -> Path:
    """Version8/ — parent of src/ when this file lives at src/config/run_context.py."""
    env = (os.environ.get("STEEL_ENGINE_ROOT") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    # src/config/run_context.py → src/ → Version8/
    return Path(__file__).resolve().parents[2]


def resolve_run_context(
    run_root_arg: Optional[PathLike] = None,
    engine_root: Optional[PathLike] = None,
) -> RunContext:
    """
    Resolve RunContext from explicit arg, environment, or offline defaults.

    Priority for run_root:
      1. run_root_arg (CLI argv)
      2. STEEL_RUN_ROOT
      3. engine_root (offline — shared Version8/data/output)
    """
    eng = Path(engine_root).expanduser().resolve() if engine_root else default_engine_root()

    run: Optional[Path] = None
    if run_root_arg is not None:
        run = Path(run_root_arg).expanduser()
        if not run.is_absolute():
            run = (eng / run).resolve()
        else:
            run = run.resolve()
    else:
        env_run = (os.environ.get("STEEL_RUN_ROOT") or "").strip()
        if env_run:
            run = Path(env_run).expanduser().resolve()

    if run is None:
        run = eng

    env_out = (os.environ.get("STEEL_OUTPUT_ROOT") or "").strip()
    if env_out:
        output_root = Path(env_out).expanduser().resolve()
    else:
        output_root = (run / "data" / "output").resolve()

    ctx = RunContext(
        engine_root=eng,
        run_root=run,
        input_root=run,
        output_root=output_root,
    )
    ctx.ensure_output_dirs()
    return ctx


def run_root_from_argv(argv: list, index: int = 1) -> Optional[Path]:
    """Return Path(argv[index]) if present, else None."""
    if len(argv) > index and str(argv[index]).strip():
        return Path(str(argv[index]).strip())
    return None
