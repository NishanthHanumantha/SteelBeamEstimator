"""
pipeline_runner.py — Executes each pipeline stage as a subprocess.
MODEL_VERSION: 7.2.0
"""

from __future__ import annotations
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import List
from .pipeline_execution_models import StageDefinition, StageResult

WORKSPACE = pathlib.Path(r"C:\Users\nishanth.h\SteelBeamEstimator")
V7        = WORKSPACE / "Version7"
PYTHON    = sys.executable


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _count_output_files(out_dir_rel: str) -> List[str]:
    d = V7 / out_dir_rel
    if not d.exists():
        return []
    return [str(f) for f in sorted(d.glob("*")) if f.is_file()]


class PipelineRunner:
    """Runs each stage script in strict sequential order."""

    def run_stage(self, stage: StageDefinition, input_beam_count: int) -> StageResult:
        script = V7 / stage.runner_script
        cmd    = [PYTHON, str(script)] + stage.cli_args

        print(f"\n  [{stage.stage_id}] Running: {script.name} ...")
        print(f"           cmd: {' '.join(cmd[-3:])}")

        start_iso  = _iso()
        t0         = time.perf_counter()

        try:
            proc = subprocess.run(
                cmd,
                cwd        = str(V7),
                capture_output = True,
                text       = True,
                timeout    = stage.timeout_s,
                encoding   = "utf-8",
                errors     = "replace",
            )
            elapsed    = round(time.perf_counter() - t0, 2)
            exit_code  = proc.returncode
            stdout_tail = (proc.stdout or "")[-2000:]
            stderr_tail = (proc.stderr or "")[-1000:]
            status     = "SUCCESS" if exit_code == 0 else "FAILED"

        except subprocess.TimeoutExpired:
            elapsed    = round(time.perf_counter() - t0, 2)
            exit_code  = -1
            stdout_tail = ""
            stderr_tail = f"TIMEOUT after {stage.timeout_s}s"
            status     = "TIMEOUT"

        except Exception as exc:
            elapsed    = round(time.perf_counter() - t0, 2)
            exit_code  = -2
            stdout_tail = ""
            stderr_tail = str(exc)
            status     = "FAILED"

        output_files = _count_output_files(stage.output_dir)
        end_iso      = _iso()

        result = StageResult(
            stage_id          = stage.stage_id,
            name              = stage.name,
            status            = status,
            exit_code         = exit_code,
            start_time        = start_iso,
            end_time          = end_iso,
            duration_s        = elapsed,
            stdout_tail       = stdout_tail,
            stderr_tail       = stderr_tail,
            output_files      = output_files,
            input_beam_count  = input_beam_count,
            output_beam_count = 0,   # filled in by BeamCountMonitor after
            beam_ids          = [],
            lost_beams        = [],
        )

        mark = "[OK]" if status == "SUCCESS" else "[FAIL]"
        print(f"  {mark} {stage.stage_id} — exit={exit_code}  "
              f"duration={elapsed}s  output_files={len(output_files)}")
        if status != "SUCCESS":
            print(f"       stderr: {stderr_tail[-300:]}")

        return result
