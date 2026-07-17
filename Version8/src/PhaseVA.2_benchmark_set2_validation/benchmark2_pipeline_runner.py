"""
Phase V.A.2 -- benchmark2_pipeline_runner.py
Execute the complete production pipeline (MODEL_VERSION 6.6.3) on Version8.
No engineering logic is modified -- orchestration only.
MODEL_VERSION: 7.0.0
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import time
from typing import List

from benchmark2_models import PipelineRunResult, PipelineStageResult

_ROOT    = pathlib.Path(__file__).resolve().parents[3]   # SteelBeamEstimator/
_V7      = _ROOT / "Version8"
_RUNNERS = _V7   / "Run_PY"

# ------------------------------------------------------------------
# Full production pipeline for MODEL_VERSION 6.6.3 on Version8.
# Order: L.2 -> L.2.2 -> L.2.1 -> L.3 -> SI.0 (chains SI.1 + V.B.1)
# ------------------------------------------------------------------
PRODUCTION_STAGES: List[dict] = [
    {
        "name": "Phase L.2 -- Engineering Reinforcement Interpretation",
        "script": "run_phase_l2_engineering_reinforcement_interpretation.py",
        "expected_outputs": [
            "Version8/data/output/PhaseL.2 - engineering_reinforcement_interpretation/beam_reinforcement_models.json",
        ],
    },
    {
        "name": "Phase L.2.2 -- Geometry Recovery & Coverage Validation",
        "script": "run_phase_l2_2_geometry_recovery.py",
        "expected_outputs": [
            "Version8/data/output/PhaseL.2.2_geometry_recovery/extended_beam_reinforcement_models.json",
        ],
    },
    {
        "name": "Phase L.2.1 -- Engineering Feature Extraction",
        "script": "run_phase_l2_1_engineering_feature_extraction.py",
        "expected_outputs": [
            "Version8/data/output/PhaseL.2.1 - engineering_feature_extraction/engineering_feature_database.json",
        ],
    },
    {
        "name": "Phase L.3 -- Beam Reinforcement Pattern Recognition",
        "script": "run_phase_l3_beam_pattern_recognition.py",
        "expected_outputs": [
            "Version8/data/output/PhaseL.3_beam_pattern_recognition/engineering_patterns.json",
        ],
    },
    {
        "name": "Phase SI.0 -- Stirrup Recovery & Interpretation Engine",
        "script": "run_phase_si0_stirrup_recovery.py",
        "expected_outputs": [
            "Version8/data/output/PhaseSI.0_stirrup_recovery/beam_reinforcement_models.json",
        ],
    },
]

# V.B.1 is chained from the SI.0 runner.  These are its final production outputs.
VB1_OUTPUTS = [
    "Version8/data/output/Production_Output/Estimation_Output.xlsx",
    "Version8/data/output/Production_Output/production_statistics.json",
    "Version8/data/output/Production_Output/engineering_totals.json",
    "Version8/data/output/Production_Output/steel_weight_summary.json",
    "Version8/data/output/Production_Output/bbs_summary.json",
]


class Benchmark2PipelineRunner:
    """
    Execute the complete Version8 production pipeline and capture stage metrics.
    Read-only with respect to engineering logic.
    """

    def __init__(self, working_dir: pathlib.Path = _V7) -> None:
        self._cwd = working_dir

    def run_all(self) -> PipelineRunResult:
        stage_results: List[PipelineStageResult] = []
        t_start = time.perf_counter()

        for stage in PRODUCTION_STAGES:
            result = self._run_stage(stage)
            stage_results.append(result)
            if not result.success:
                print(
                    f"  [WARN] Stage '{stage['name']}' completed with issues "
                    f"(exit={result.exit_code}). Continuing pipeline."
                )

        # V.B.1 chained output record (pseudo-stage)
        vb1_found = [str(_ROOT / p) for p in VB1_OUTPUTS if (_ROOT / p).exists()]
        stage_results.append(
            PipelineStageResult(
                stage_name="Phase V.B.1 -- Production Output Completion (via SI.0)",
                script_path="(chained from SI.0 runner)",
                success=bool(vb1_found),
                exit_code=0 if vb1_found else -1,
                elapsed_seconds=0.0,
                stdout_lines=0,
                output_files=vb1_found,
                error_message="" if vb1_found else "Production Output files not found",
            )
        )

        total_elapsed = round(time.perf_counter() - t_start, 2)
        passed = sum(1 for r in stage_results if r.success)
        failed = len(stage_results) - passed

        return PipelineRunResult(
            stages=stage_results,
            total_elapsed_seconds=total_elapsed,
            stages_executed=len(stage_results),
            stages_passed=passed,
            stages_failed=failed,
            success_rate_pct=round(100 * passed / len(stage_results), 2) if stage_results else 0.0,
            pipeline_passed=(failed == 0),
        )

    def _run_stage(self, stage: dict) -> PipelineStageResult:
        name   = stage["name"]
        script = _RUNNERS / stage["script"]
        exp_out = [_ROOT / o for o in stage.get("expected_outputs", [])]

        print(f"  [RUNNING] {name}")

        if not script.exists():
            return PipelineStageResult(
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

            return PipelineStageResult(
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
            return PipelineStageResult(
                stage_name=name,
                script_path=str(script),
                success=False,
                exit_code=-2,
                elapsed_seconds=round(time.perf_counter() - t0, 2),
                stdout_lines=0,
                error_message="Stage timed out (>600s)",
            )
        except Exception as exc:
            return PipelineStageResult(
                stage_name=name,
                script_path=str(script),
                success=False,
                exit_code=-3,
                elapsed_seconds=round(time.perf_counter() - t0, 2),
                stdout_lines=0,
                error_message=str(exc),
            )
