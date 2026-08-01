"""
pipeline_runner.py — Invoke the existing Version8 production pipeline.

Reuses production stage list and RunContext env vars.
Does NOT modify engineering logic — orchestration only.

MODEL_VERSION: 8.9.0
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

MODEL_VERSION = "8.9.0"

# Mirror webapp/config.PRODUCTION_STAGES — keep in sync; do not import Flask app.
PRODUCTION_STAGES: List[Dict[str, Any]] = [
    {"id": "VROOT1", "script": "Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py", "timeout_s": 300},
    {"id": "R1",     "script": "Run_PY/run_phase_r1_generalized_reinforcement_discovery.py", "timeout_s": 900},
    {"id": "T1",     "script": "Run_PY/run_phase_t1_geometric_stirrup_evidence.py", "timeout_s": 1200},
    {"id": "R2A",    "script": "Run_PY/run_phase_r2a_engineering_context.py", "timeout_s": 300},
    {"id": "R21B",   "script": "Run_PY/run_phase_r21b_semantic_interpreter.py", "timeout_s": 900},
    {"id": "R21C",   "script": "Run_PY/run_phase_r21c_engineering_fact_normalization.py", "timeout_s": 600},
    {"id": "R21D",   "script": "Run_PY/run_phase_r21d_evidence_hypothesis_engine.py", "timeout_s": 600},
    {"id": "L22",    "script": "Run_PY/run_phase_l2_2_geometry_recovery.py", "timeout_s": 300},
    {"id": "R3",     "script": "Run_PY/run_phase_r3_geometry_context_engine.py", "timeout_s": 900},
    {"id": "R31",    "script": "Run_PY/run_phase_r31_engineering_relationship_engine.py", "timeout_s": 900},
    {"id": "R12A",   "script": "Run_PY/run_phase_r12a_geometry_accuracy.py", "timeout_s": 600},
    {"id": "R13",    "script": "Run_PY/run_phase_r13_pipeline_integration.py", "timeout_s": 1200},
    {"id": "VB1",    "script": "Run_PY/run_phase_vb1_production_output_completion.py", "timeout_s": 900},
]

VB1_EXCEL_REL = "data/output/Production_Output/Estimation_Output.xlsx"

# Soft-success artefact checks (same philosophy as webapp estimation_service)
_SOFT_ARTEFACTS = {
    "R3":   "data/output/PhaseR3_geometry_context_engine/GeometryContexts.json",
    "R31":  "data/output/PhaseR3.1_engineering_relationship_engine/EngineeringDrawingRelationships.json",
    "R12A": "data/output/PhaseR1_2A_geometry_accuracy/validated_beam_geometry.json",
    "R13":  "data/output/PhaseR1.3_pipeline_integration/beam_reinforcement_models_production.json",
    "VB1":  VB1_EXCEL_REL,
    "L22":  "data/output/PhaseL.2.2_geometry_recovery/geometry_registry.json",
    "R21D": "data/output/PhaseR2.1D_evidence_hypothesis_engine/EngineeringFacts.json",
    "R21C": "data/output/PhaseR2.1C_engineering_fact_normalization/EngineeringFacts.json",
    "T1":   "data/output/PhaseT1_geometric_stirrup_evidence/stirrup_geometry_evidence.json",
}


@dataclass
class StageResult:
    stage_id: str
    success: bool
    exit_code: int
    elapsed_s: float
    soft_success: bool = False
    error_tail: str = ""


@dataclass
class PipelineResult:
    drawing_set: str
    run_root: Path
    model_excel: Optional[Path]
    success: bool
    elapsed_s: float
    stages: List[StageResult] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "drawing_set": self.drawing_set,
            "run_root": str(self.run_root),
            "model_excel": str(self.model_excel) if self.model_excel else None,
            "success": self.success,
            "elapsed_s": self.elapsed_s,
            "error": self.error,
            "stages": [
                {
                    "stage_id": s.stage_id,
                    "success": s.success,
                    "exit_code": s.exit_code,
                    "elapsed_s": s.elapsed_s,
                    "soft_success": s.soft_success,
                }
                for s in self.stages
            ],
        }


class ProductionPipelineRunner:
    """
    Stage Drawing Set DXFs into an isolated web_run and execute production stages.
    """

    def __init__(self, v8_root: Path):
        self.v8 = Path(v8_root).resolve()
        self.web_runs = self.v8 / "data" / "web_runs"
        self.r2a_pointer = (
            self.v8 / "src" / "PhaseVROOT.1_dynamic_pipeline_initialization" / "beam_registry.json"
        )

    def stage_drawing_set(
        self,
        drawing_set_name: str,
        general_notes: Path,
        framing: Path,
        reinforcement: Path,
    ) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in drawing_set_name)
        run_id = f"qa2_{safe}_{stamp}"
        run_root = self.web_runs / run_id
        for sub in ("general_notes", "framing", "reinforcement"):
            (run_root / sub).mkdir(parents=True, exist_ok=True)
        (run_root / "data" / "output").mkdir(parents=True, exist_ok=True)

        shutil.copy2(general_notes, run_root / "general_notes" / general_notes.name)
        shutil.copy2(framing, run_root / "framing" / framing.name)
        shutil.copy2(reinforcement, run_root / "reinforcement" / reinforcement.name)
        return run_root

    def run(
        self,
        drawing_set_name: str,
        general_notes: Path,
        framing: Path,
        reinforcement: Path,
        run_root: Optional[Path] = None,
    ) -> PipelineResult:
        t0 = time.perf_counter()
        if run_root is None:
            run_root = self.stage_drawing_set(
                drawing_set_name, general_notes, framing, reinforcement
            )
        gn_path = next((run_root / "general_notes").glob("*.dxf"), None)
        if gn_path is None:
            return PipelineResult(
                drawing_set=drawing_set_name,
                run_root=run_root,
                model_excel=None,
                success=False,
                elapsed_s=0.0,
                error="No general notes DXF in staged run",
            )

        self._write_gn_pointer(gn_path)
        stages: List[StageResult] = []
        try:
            for stage in PRODUCTION_STAGES:
                sr = self._run_stage(stage, run_root)
                stages.append(sr)
                if not sr.success:
                    excel = run_root / VB1_EXCEL_REL
                    return PipelineResult(
                        drawing_set=drawing_set_name,
                        run_root=run_root,
                        model_excel=excel if excel.exists() else None,
                        success=False,
                        elapsed_s=round(time.perf_counter() - t0, 2),
                        stages=stages,
                        error=f"Stage {stage['id']} failed (exit={sr.exit_code})",
                    )
        finally:
            self._clear_gn_pointer()

        excel = run_root / VB1_EXCEL_REL
        return PipelineResult(
            drawing_set=drawing_set_name,
            run_root=run_root,
            model_excel=excel if excel.exists() else None,
            success=excel.exists(),
            elapsed_s=round(time.perf_counter() - t0, 2),
            stages=stages,
            error="" if excel.exists() else "Estimation_Output.xlsx not produced",
        )

    def _run_stage(self, stage: Dict[str, Any], run_root: Path) -> StageResult:
        script = self.v8 / stage["script"]
        cmd = [sys.executable, str(script), str(run_root)]
        env = os.environ.copy()
        env["STEEL_ENGINE_ROOT"] = str(self.v8)
        env["STEEL_RUN_ROOT"] = str(run_root)
        env["STEEL_OUTPUT_ROOT"] = str(run_root / "data" / "output")

        t0 = time.perf_counter()
        proc = subprocess.run(
            cmd,
            cwd=str(self.v8),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=int(stage.get("timeout_s") or 600),
        )
        elapsed = round(time.perf_counter() - t0, 2)
        soft = False
        ok = proc.returncode == 0
        if not ok:
            rel = _SOFT_ARTEFACTS.get(stage["id"])
            if rel and (run_root / rel).exists():
                ok = True
                soft = True
        tail = ""
        if not ok:
            tail = ((proc.stderr or proc.stdout or "")[-2000:]).strip()
        return StageResult(
            stage_id=stage["id"],
            success=ok,
            exit_code=proc.returncode,
            elapsed_s=elapsed,
            soft_success=soft,
            error_tail=tail,
        )

    def _write_gn_pointer(self, gn_path: Path) -> None:
        self.r2a_pointer.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "general_notes_dxf": str(gn_path.resolve()),
            "project_id": "QA2_BENCHMARK",
            "source": "QA.2_POINTER",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.r2a_pointer.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _clear_gn_pointer(self) -> None:
        try:
            if self.r2a_pointer.exists():
                data = json.loads(self.r2a_pointer.read_text(encoding="utf-8"))
                if data.get("source") == "QA.2_POINTER":
                    self.r2a_pointer.unlink(missing_ok=True)
        except Exception:
            pass
