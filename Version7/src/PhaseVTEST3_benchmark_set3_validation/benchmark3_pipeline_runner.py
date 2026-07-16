"""
benchmark3_pipeline_runner.py — Execute complete production pipeline on Set 3.
MODEL_VERSION: 8.1.1

READ-ONLY orchestration. No engineering logic modified.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import time
from typing import List

from benchmark3_models import PipelineRunResult, PipelineStageResult

_ROOT    = pathlib.Path(__file__).resolve().parents[3]
_V7      = _ROOT / "Version7"
_RUNNERS = _V7 / "Run_PY"

# Complete pipeline per V.TEST.3 specification
PRODUCTION_STAGES: List[dict] = [
    {
        "id": "VROOT1",
        "name": "Phase V.ROOT.1 — Dynamic Pipeline Initialization",
        "script": "run_phase_vroot1_dynamic_pipeline_initialization.py",
        "args": ["data/Benchmark_Set_3"],
        "expected_outputs": [
            "data/output/PhaseVROOT.1_dynamic_pipeline_initialization/beam_registry.json",
        ],
        "timeout": 180,
    },
    {
        "id": "R1",
        "name": "Phase R.1 — Generalized Reinforcement Discovery",
        "script": "run_phase_r1_generalized_reinforcement_discovery.py",
        "args": [],
        "expected_outputs": [
            "data/output/PhaseR.1_generalized_reinforcement_discovery/reinforcement_annotations.json",
        ],
        "timeout": 600,
    },
    {
        "id": "R20",
        "name": "Phase R.2.0 — MTEXT Engineering Text Recovery",
        "script": "run_phase_r20_mtext_recovery.py",
        "args": [],
        "expected_outputs": [
            "data/output/PhaseR2.0_mtext_engineering_text_recovery/engineering_text_recovery.json",
        ],
        "timeout": 300,
    },
    {
        "id": "R201",
        "name": "Phase R.2.0.1 — Engineering Notation Inventory",
        "script": "run_phase_r201_notation_inventory.py",
        "args": [],
        "expected_outputs": [
            "data/output/PhaseR2.0.1_engineering_notation_inventory/engineering_notation_inventory.json",
        ],
        "timeout": 300,
    },
    {
        "id": "R21A",
        "name": "Phase R.2.1A — Engineering Semantic Dictionary",
        "script": "run_phase_r21a_semantic_dictionary.py",
        "args": [],
        "expected_outputs": [
            "data/output/PhaseR2.1A_engineering_semantic_dictionary/engineering_semantic_dictionary.json",
        ],
        "timeout": 300,
    },
    {
        "id": "R21B",
        "name": "Phase R.2.1B — Engineering Semantic Interpreter",
        "script": "run_phase_r21b_semantic_interpreter.py",
        "args": [],
        "expected_outputs": [
            "data/output/PhaseR2.1B_engineering_semantic_interpreter/engineering_semantic_objects.json",
        ],
        "timeout": 600,
    },
    {
        "id": "R21C",
        "name": "Phase R.2.1C — Engineering Fact Normalization",
        "script": "run_phase_r21c_engineering_fact_normalization.py",
        "args": [],
        "expected_outputs": [
            "data/output/PhaseR2.1C_engineering_fact_normalization/EngineeringFacts.json",
        ],
        "timeout": 600,
    },
    {
        "id": "R21D",
        "name": "Phase R.2.1D — Evidence & Intent Hypothesis Engine",
        "script": "run_phase_r21d_evidence_hypothesis_engine.py",
        "args": [],
        "expected_outputs": [
            "data/output/PhaseR2.1D_evidence_hypothesis_engine/EngineeringFacts.json",
        ],
        "timeout": 600,
    },
    {
        "id": "R3",
        "name": "Phase R.3 — Geometry Context Engine",
        "script": "run_phase_r3_geometry_context_engine.py",
        "args": [],
        "expected_outputs": [
            "data/output/PhaseR3_geometry_context_engine/GeometryContexts.json",
        ],
        "timeout": 600,
    },
    {
        "id": "R31",
        "name": "Phase R.3.1 — Engineering Drawing Relationship Engine",
        "script": "run_phase_r31_engineering_relationship_engine.py",
        "args": [],
        "expected_outputs": [
            "data/output/PhaseR3.1_engineering_relationship_engine/EngineeringDrawingRelationships.json",
        ],
        "timeout": 600,
    },
    {
        "id": "R13",
        "name": "Phase R.1.3 — Pipeline Integration",
        "script": "run_phase_r13_pipeline_integration.py",
        "args": [],
        "expected_outputs": [
            "data/output/PhaseR1.3_pipeline_integration/engineering_bar_models.json",
        ],
        "timeout": 900,
    },
    {
        "id": "R14",
        "name": "Phase R.1.4 — Integrity Validation",
        "script": "run_phase_r14_integrity_validation.py",
        "args": [],
        "expected_outputs": [
            "data/output/PhaseR1.4_integrity_validation/integrity_validation.json",
        ],
        "timeout": 300,
    },
    {
        "id": "R2A",
        "name": "Phase R.2A — Engineering Context",
        "script": "run_phase_r2a_engineering_context.py",
        "args": [],
        "expected_outputs": [
            "data/output/PhaseR.2A_engineering_context/engineering_context.json",
        ],
        "timeout": 300,
    },
    {
        "id": "R2B",
        "name": "Phase R.2B — Engineering Context Consumption",
        "script": "run_phase_r2b_engineering_context_consumption.py",
        "args": [],
        "expected_outputs": [
            "data/output/PhaseR.2B_engineering_context_consumption/engineering_context_consumption_report.json",
        ],
        "timeout": 900,
    },
    {
        "id": "VB1",
        "name": "Phase V.B.1 — Production Output Completion",
        "script": "run_phase_vb1_production_output_completion.py",
        "args": [],
        "expected_outputs": [
            "data/output/Production_Output/Estimation_Output.xlsx",
            "data/output/Production_Output/production_statistics.json",
        ],
        "timeout": 900,
    },
]


class Benchmark3PipelineRunner:

    def __init__(self, working_dir: pathlib.Path = _V7) -> None:
        self._cwd = working_dir

    def run_all(self) -> PipelineRunResult:
        stage_results: List[PipelineStageResult] = []
        t_start = time.perf_counter()

        for stage in PRODUCTION_STAGES:
            result = self._run_stage(stage)
            stage_results.append(result)
            icon = "OK" if result.success else "WARN"
            print(f"  [{icon}] {stage['id']}: exit={result.exit_code} "
                  f"elapsed={result.elapsed_seconds:.1f}s")
            if not result.success:
                print(f"       {result.error_message[:120]}")

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
            pipeline_completed=(failed == 0),
        )

    def _run_stage(self, stage: dict) -> PipelineStageResult:
        name    = stage["name"]
        stage_id = stage["id"]
        script  = _RUNNERS / stage["script"]
        args    = stage.get("args", [])
        exp_out = [_V7 / o for o in stage.get("expected_outputs", [])]
        timeout = stage.get("timeout", 600)

        if not script.exists():
            return PipelineStageResult(
                stage_id=stage_id,
                stage_name=name,
                script_path=str(script),
                success=False,
                exit_code=-1,
                elapsed_seconds=0.0,
                error_message=f"Runner not found: {script}",
            )

        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, str(script)] + args,
                cwd=str(self._cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            elapsed   = round(time.perf_counter() - t0, 2)
            out_found = [str(p) for p in exp_out if p.exists()]
            success   = proc.returncode == 0

            return PipelineStageResult(
                stage_id=stage_id,
                stage_name=name,
                script_path=str(script),
                success=success,
                exit_code=proc.returncode,
                elapsed_seconds=elapsed,
                output_files=out_found,
                stderr_tail=(proc.stderr or "")[-1500:],
                error_message="" if success else (
                    f"exit={proc.returncode}"
                    + (f", outputs={len(out_found)}/{len(exp_out)}" if exp_out else "")
                ),
            )
        except subprocess.TimeoutExpired:
            return PipelineStageResult(
                stage_id=stage_id,
                stage_name=name,
                script_path=str(script),
                success=False,
                exit_code=-2,
                elapsed_seconds=round(time.perf_counter() - t0, 2),
                error_message=f"Timeout after {timeout}s",
            )
        except Exception as exc:
            return PipelineStageResult(
                stage_id=stage_id,
                stage_name=name,
                script_path=str(script),
                success=False,
                exit_code=-3,
                elapsed_seconds=round(time.perf_counter() - t0, 2),
                error_message=str(exc),
            )
