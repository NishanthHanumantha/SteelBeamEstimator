"""
Phase V.A.1 — End-to-End Validation
pipeline_runner.py — Execute the complete production pipeline without modification.
MODEL_VERSION: 6.5.3

Runs each existing runner script in sequence via subprocess.
No stage is bypassed. No code is modified.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import time
from typing import List

from validation_models import StageResult

_ROOT = pathlib.Path(__file__).resolve().parents[3]   # SteelBeamEstimator/
_V6 = _ROOT / "Version6"
_RUNNERS = _V6 / "Run_PY"


# Production pipeline stages in execution order
PRODUCTION_STAGES = [
    {
        "name": "Phase L.2 — Engineering Reinforcement Interpretation",
        "script": "run_phase_l2_engineering_reinforcement_interpretation.py",
        "expected_outputs": [
            "Version6/data/output/PhaseL.2 - engineering_reinforcement_interpretation/beam_reinforcement_models.json"
        ],
    },
    {
        "name": "Phase L.2.2 — Geometry Recovery & Coverage Validation",
        "script": "run_phase_l2_2_geometry_recovery.py",
        "expected_outputs": [
            "Version6/data/output/PhaseL.2.2_geometry_recovery/extended_beam_reinforcement_models.json"
        ],
    },
    {
        "name": "Phase L.2.1 — Engineering Feature Extraction",
        "script": "run_phase_l2_1_engineering_feature_extraction.py",
        "expected_outputs": [
            "Version6/data/output/PhaseL.2.1 - engineering_feature_extraction/engineering_feature_database.json"
        ],
    },
    {
        "name": "Phase L.3 — Beam Reinforcement Pattern Recognition",
        "script": "run_phase_l3_beam_pattern_recognition.py",
        "expected_outputs": [
            "Version6/data/output/PhaseL.3_beam_pattern_recognition/engineering_patterns.json"
        ],
    },
    {
        "name": "Phase I — Steel Calculation & BBS & Excel Export",
        "script": "run_engineering_calculation_integration.py",
        "expected_outputs": [
            "Version6/data/output/phase_i/i_17_excel_export/Beam_Reinforcement_Schedule.xlsx"
        ],
    },
]


class PipelineRunner:
    """
    Executes the complete V6 production pipeline.
    Read-only with respect to pipeline logic — only orchestrates execution.
    """

    def __init__(self, working_dir: pathlib.Path = _V6) -> None:
        self._cwd = working_dir

    def run_all(self) -> List[StageResult]:
        results: List[StageResult] = []
        for stage in PRODUCTION_STAGES:
            result = self._run_stage(stage)
            results.append(result)
            if not result.success:
                print(f"  [WARN] Stage '{stage['name']}' failed with exit code {result.exit_code}")
                print(f"         Continuing to collect remaining stage results…")
        return results

    def _run_stage(self, stage: dict) -> StageResult:
        name = stage["name"]
        script = _RUNNERS / stage["script"]
        expected_outs = [_ROOT / o for o in stage.get("expected_outputs", [])]

        print(f"  [RUNNING] {name}")
        if not script.exists():
            return StageResult(
                stage_name=name,
                script_path=str(script),
                success=False,
                exit_code=-1,
                elapsed_seconds=0.0,
                stdout_lines=0,
                stderr="",
                error_message=f"Runner script not found: {script}",
            )

        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, str(script)],
                cwd=str(self._cwd),
                capture_output=True,
                text=True,
                timeout=300,
            )
            elapsed = time.perf_counter() - t0
            success = proc.returncode == 0

            stdout_lines = len(proc.stdout.splitlines())
            stderr_tail = proc.stderr[-2000:] if proc.stderr else ""

            output_files = [str(p) for p in expected_outs if p.exists()]

            return StageResult(
                stage_name=name,
                script_path=str(script),
                success=success,
                exit_code=proc.returncode,
                elapsed_seconds=round(elapsed, 2),
                stdout_lines=stdout_lines,
                stderr=stderr_tail,
                error_message="" if success else f"Exit code {proc.returncode}",
                output_files=output_files,
            )
        except subprocess.TimeoutExpired:
            elapsed = time.perf_counter() - t0
            return StageResult(
                stage_name=name,
                script_path=str(script),
                success=False,
                exit_code=-2,
                elapsed_seconds=round(elapsed, 2),
                stdout_lines=0,
                stderr="",
                error_message="Stage timed out after 300s",
            )
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            return StageResult(
                stage_name=name,
                script_path=str(script),
                success=False,
                exit_code=-3,
                elapsed_seconds=round(elapsed, 2),
                stdout_lines=0,
                stderr="",
                error_message=str(exc),
            )

    def summarise(self, results: List[StageResult]) -> dict:
        total = len(results)
        passed = sum(1 for r in results if r.success)
        failed = total - passed
        total_time = sum(r.elapsed_seconds for r in results)
        return {
            "stages_executed": total,
            "stages_passed": passed,
            "stages_failed": failed,
            "total_elapsed_seconds": round(total_time, 2),
            "success_rate_pct": round(100 * passed / total, 2) if total else 0.0,
            "stages": [
                {
                    "name": r.stage_name,
                    "success": r.success,
                    "exit_code": r.exit_code,
                    "elapsed_seconds": r.elapsed_seconds,
                    "stdout_lines": r.stdout_lines,
                    "output_files_found": r.output_files,
                    "error": r.error_message,
                }
                for r in results
            ],
        }
