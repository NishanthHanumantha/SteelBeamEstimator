"""
Phase V.A.1.1 — pipeline_recompute_runner.py
Execute the complete production pipeline (MODEL_VERSION 6.6.2) via subprocess.
No engineering logic is modified — only orchestrates execution.
MODEL_VERSION: 6.6.3
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import time
from typing import List

from validation_recompute_models import (
    PipelineRecomputeResult,
    StageRecomputeResult,
)

_ROOT    = pathlib.Path(__file__).resolve().parents[3]   # SteelBeamEstimator/
_V6      = _ROOT / "Version7"
_RUNNERS = _V6 / "Run_PY"

# ── Full production pipeline for MODEL_VERSION 6.6.2 ──────────────────────────
# Runs: L.2 -> SI.0 (which internally chains SI.1 -> V.B.1)
# Then L.2.2 -> L.2.1 -> L.3 as pre-passes (already done, but re-execute for capture)
PRODUCTION_STAGES: List[dict] = [
    {
        "name": "Phase L.2 — Engineering Reinforcement Interpretation",
        "script": "run_phase_l2_engineering_reinforcement_interpretation.py",
        "expected_outputs": [
            "Version7/data/output/PhaseL.2 - engineering_reinforcement_interpretation/beam_reinforcement_models.json"
        ],
    },
    {
        "name": "Phase L.2.2 — Geometry Recovery & Coverage Validation",
        "script": "run_phase_l2_2_geometry_recovery.py",
        "expected_outputs": [
            "Version7/data/output/PhaseL.2.2_geometry_recovery/extended_beam_reinforcement_models.json"
        ],
    },
    {
        "name": "Phase L.2.1 — Engineering Feature Extraction",
        "script": "run_phase_l2_1_engineering_feature_extraction.py",
        "expected_outputs": [
            "Version7/data/output/PhaseL.2.1 - engineering_feature_extraction/engineering_feature_database.json"
        ],
    },
    {
        "name": "Phase L.3 — Beam Reinforcement Pattern Recognition",
        "script": "run_phase_l3_beam_pattern_recognition.py",
        "expected_outputs": [
            "Version7/data/output/PhaseL.3_beam_pattern_recognition/engineering_patterns.json"
        ],
    },
    {
        "name": "Phase SI.0 — Stirrup Recovery & Interpretation Engine",
        "script": "run_phase_si0_stirrup_recovery.py",
        "expected_outputs": [
            "Version7/data/output/PhaseSI.0_stirrup_recovery/beam_reinforcement_models.json"
        ],
    },
    # SI.0 runner internally chains SI.1 -> V.B.1.
    # The following stages verify the V.B.1 output (no re-execution needed,
    # but we capture their latest output paths for the report).
]

# V.B.1 final outputs to record even if not re-executed as separate stages
VB1_OUTPUTS = [
    "Version7/data/output/Production_Output/Estimation_Output.xlsx",
    "Version7/data/output/Production_Output/production_statistics.json",
    "Version7/data/output/Production_Output/engineering_totals.json",
    "Version7/data/output/Production_Output/steel_weight_summary.json",
    "Version7/data/output/Production_Output/bbs_summary.json",
]


class PipelineRecomputeRunner:
    """
    Executes the complete production pipeline and captures all stage results.
    Read-only with respect to pipeline logic — no engineering code is modified.
    """

    def __init__(self, working_dir: pathlib.Path = _V6) -> None:
        self._cwd = working_dir

    def run_all(self) -> PipelineRecomputeResult:
        stage_results: List[StageRecomputeResult] = []
        t_total_start = time.perf_counter()

        for stage in PRODUCTION_STAGES:
            result = self._run_stage(stage)
            stage_results.append(result)
            if not result.success:
                print(
                    f"  [WARN] Stage '{stage['name']}' failed "
                    f"(exit={result.exit_code}). Continuing."
                )

        # Record V.B.1 final outputs as a pseudo-stage (already run by SI.0)
        vb1_found = [str(_ROOT / p) for p in VB1_OUTPUTS if (_ROOT / p).exists()]
        stage_results.append(
            StageRecomputeResult(
                stage_name="Phase V.B.1 — Production Output Completion (via SI.0)",
                script_path="(chained from SI.0 runner)",
                success=bool(vb1_found),
                exit_code=0 if vb1_found else -1,
                elapsed_seconds=0.0,
                stdout_lines=0,
                output_files=vb1_found,
                error_message="" if vb1_found else "Production Output files not found",
            )
        )

        total_elapsed = round(time.perf_counter() - t_total_start, 2)
        passed = sum(1 for r in stage_results if r.success)
        failed = len(stage_results) - passed

        return PipelineRecomputeResult(
            stages=stage_results,
            total_elapsed_seconds=total_elapsed,
            stages_executed=len(stage_results),
            stages_passed=passed,
            stages_failed=failed,
            success_rate_pct=round(100 * passed / len(stage_results), 2) if stage_results else 0.0,
            pipeline_passed=(failed == 0),
        )

    def _run_stage(self, stage: dict) -> StageRecomputeResult:
        name    = stage["name"]
        script  = _RUNNERS / stage["script"]
        exp_out = [_ROOT / o for o in stage.get("expected_outputs", [])]

        print(f"  [RUNNING] {name}")

        if not script.exists():
            return StageRecomputeResult(
                stage_name=name,
                script_path=str(script),
                success=False,
                exit_code=-1,
                elapsed_seconds=0.0,
                stdout_lines=0,
                error_message=f"Runner script not found: {script}",
            )

        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, str(script)],
                cwd=str(self._cwd),
                capture_output=True,
                text=True,
                timeout=600,
            )
            elapsed   = round(time.perf_counter() - t0, 2)
            success   = proc.returncode == 0
            out_found = [str(p) for p in exp_out if p.exists()]

            return StageRecomputeResult(
                stage_name=name,
                script_path=str(script),
                success=success,
                exit_code=proc.returncode,
                elapsed_seconds=elapsed,
                stdout_lines=len(proc.stdout.splitlines()),
                stderr=proc.stderr[-2000:] if proc.stderr else "",
                error_message="" if success else f"Exit code {proc.returncode}",
                output_files=out_found,
            )
        except subprocess.TimeoutExpired:
            return StageRecomputeResult(
                stage_name=name,
                script_path=str(script),
                success=False,
                exit_code=-2,
                elapsed_seconds=round(time.perf_counter() - t0, 2),
                stdout_lines=0,
                error_message="Stage timed out (>600s)",
            )
        except Exception as exc:
            return StageRecomputeResult(
                stage_name=name,
                script_path=str(script),
                success=False,
                exit_code=-3,
                elapsed_seconds=round(time.perf_counter() - t0, 2),
                stdout_lines=0,
                error_message=str(exc),
            )
