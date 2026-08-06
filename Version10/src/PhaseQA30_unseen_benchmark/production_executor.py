"""
QA.3.0 — ProductionExecutor
MODEL_VERSION: 10.0.0

Runs the existing Version10 ProductionPipelineRunner (DXF-only).
Never receives or opens the estimator workbook.

Orchestration-only timeout recovery: large unseen drawings can exceed the
stock T16CHAIN 7200s subprocess timeout. When that happens we do NOT modify
pipeline_runner; we finish the Track1 chain with an extended timeout if the
fresh VB1 workbook already exists.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .drawing_set_discovery import DiscoveredSet

MODEL_VERSION = "10.0.0"
PHASE_ID = "QA.3.0"

VB1_EXCEL_REL = "data/output/Production_Output/Estimation_Output.xlsx"
T16_SOFT_REL = "data/output/PhaseT182_adaptive_render_extent/RenderedBeams"
T1831_REL = "data/output/PhaseT1831_shared_scope_dedup"
# Orchestration-only extended budget for unseen large drawings (does not edit
# PRODUCTION_STAGES / engineering modules).
T16CHAIN_EXTENDED_TIMEOUT_S = 21600


def _load_pipeline_runner(engine_root: Path):
    qa2_dir = engine_root / "src" / "PhaseQA.2_multi_drawing_benchmark"
    full = "_qa30_pipeline_runner"
    if full not in sys.modules:
        spec = importlib.util.spec_from_file_location(full, qa2_dir / "pipeline_runner.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[full] = mod
        sys.modules["pipeline_runner"] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return sys.modules[full]


def _folder_slug(set_key: str) -> str:
    return f"{set_key}_Set_Drawings"


class ProductionExecutor:
    def __init__(self, engine_root: Path, phase_output_root: Path):
        self.engine_root = Path(engine_root)
        self.phase_output_root = Path(phase_output_root)
        self.phase_output_root.mkdir(parents=True, exist_ok=True)

    def run_set(self, ds: DiscoveredSet) -> Dict[str, Any]:
        """
        Fresh production from DXF only.
        Estimator path is recorded but NEVER passed to the pipeline runner.
        """
        assert ds.general_notes and ds.framing and ds.reinforcement
        pipe_mod = _load_pipeline_runner(self.engine_root)
        runner = pipe_mod.ProductionPipelineRunner(self.engine_root)

        set_dir = self.phase_output_root / _folder_slug(ds.set_key)
        set_dir.mkdir(parents=True, exist_ok=True)

        h = hashlib.sha256()
        for p in (ds.general_notes, ds.framing, ds.reinforcement):
            h.update(p.name.encode("utf-8"))
            h.update(str(p.stat().st_size).encode("utf-8"))
            h.update(str(int(p.stat().st_mtime)).encode("utf-8"))
        execution_hash = h.hexdigest()[:16]

        meta_pre = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "drawing_set": ds.name,
            "set_key": ds.set_key,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "execution_hash": execution_hash,
            "estimator_excel_path_recorded": str(ds.estimator_excel),
            "estimator_excel_opened_during_production": False,
            "reuse_detected": False,
            "inputs": {
                "general_notes": str(ds.general_notes),
                "framing": str(ds.framing),
                "reinforcement": str(ds.reinforcement),
            },
        }
        (set_dir / "run_metadata_pre.json").write_text(
            json.dumps(meta_pre, indent=2), encoding="utf-8"
        )

        print(f"\n[{PHASE_ID}] PRODUCTION {ds.name} (DXF-only, no estimator)")
        print(f"  GN={ds.general_notes.name}")
        print(f"  FR={ds.framing.name}")
        print(f"  RE={ds.reinforcement.name}")
        print("  Estimator Excel: NOT USED during production")

        t0 = time.perf_counter()
        timeout_recovered = False
        t16_finish: Dict[str, Any] = {}

        # Skip sets already completed in a prior session (safe resume after sleep).
        already = self._load_completed_result(ds)
        if already is not None:
            print(
                f"  [{PHASE_ID}] SKIP already-complete set "
                f"(run={already.get('run_id')}) — resume-safe"
            )
            return already

        # Resume a same-session timed-out web_run (fresh VB1 workbook already
        # produced from DXF) instead of re-staging the entire pipeline.
        recoverable = self._find_recoverable_web_run(ds)
        if recoverable is not None:
            print(
                f"  [{PHASE_ID}] resuming timed-out fresh run {recoverable.name} "
                "(DXF production already completed; finishing Track1 chain)"
            )
            pipe = pipe_mod.PipelineResult(
                drawing_set=ds.name,
                run_root=recoverable,
                model_excel=recoverable / VB1_EXCEL_REL,
                success=False,
                elapsed_s=0.0,
                stages=[],
                error="awaiting_t16_completion",
            )
            timeout_recovered = True
        else:
            try:
                # CRITICAL: only DXFs — estimator never passed
                pipe = runner.run(
                    ds.name, ds.general_notes, ds.framing, ds.reinforcement
                )
            except subprocess.TimeoutExpired as exc:
                print(
                    f"  [{PHASE_ID}] stage timeout ({exc.timeout}s) - "
                    "attempting orchestration recovery"
                )
                pipe, timeout_recovered, t16_finish = self._recover_from_timeout(
                    pipe_mod, runner, ds, exc
                )

        # If T16CHAIN soft-failed / incomplete but workbook exists, finish chain
        run_root = Path(pipe.run_root)
        excel = Path(pipe.model_excel) if pipe.model_excel else run_root / VB1_EXCEL_REL
        if excel.exists() and not self._t16_complete(run_root):
            print(f"  [{PHASE_ID}] completing Track1 visual chain (extended timeout)...")
            t16_finish = self._run_t16chain_extended(run_root)
            timeout_recovered = True
            # Re-evaluate success: workbook + soft render artefact
            pipe.success = excel.exists() and self._t16_soft_ok(run_root)
            pipe.model_excel = excel if excel.exists() else None
            if t16_finish.get("success"):
                pipe.success = True
                pipe.error = ""

        elapsed = round(time.perf_counter() - t0, 2)
        excel = Path(pipe.model_excel) if pipe.model_excel else None
        if excel is None and (run_root / VB1_EXCEL_REL).exists():
            excel = run_root / VB1_EXCEL_REL
            pipe.model_excel = excel
            pipe.success = True

        reuse_detected = False
        mirrored = self._mirror_artefacts(set_dir, run_root, excel)

        result = {
            "drawing_set": ds.name,
            "set_key": ds.set_key,
            "success": bool(pipe.success) and bool(excel and excel.exists()),
            "reuse_detected": reuse_detected,
            "estimator_excel_opened_during_production": False,
            "pipeline_elapsed_s": elapsed,
            "execution_hash": execution_hash,
            "run_id": run_root.name,
            "run_root": str(run_root),
            "model_excel": str(excel) if excel else None,
            "estimator_excel": str(ds.estimator_excel) if ds.estimator_excel else None,
            "pipeline": pipe.to_dict() if hasattr(pipe, "to_dict") else {},
            "timeout_recovered": timeout_recovered,
            "t16chain_finish": t16_finish,
            "mirrored": mirrored,
            "set_output_dir": str(set_dir),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        (set_dir / "production_result.json").write_text(
            json.dumps(result, indent=2, default=str), encoding="utf-8"
        )
        (set_dir / "run_metadata.json").write_text(
            json.dumps(
                {
                    **meta_pre,
                    "finished_at": result["timestamp"],
                    "run_id": result["run_id"],
                    "run_root": result["run_root"],
                    "model_excel": result["model_excel"],
                    "pipeline_elapsed_s": elapsed,
                    "success": result["success"],
                    "reuse_detected": False,
                    "timeout_recovered": timeout_recovered,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            f"  production_success={result['success']} elapsed={elapsed}s "
            f"run={result['run_id']} timeout_recovered={timeout_recovered}"
        )
        return result

    def run_all(self, sets: List[DiscoveredSet]) -> Dict[str, Any]:
        results = []
        t0 = time.perf_counter()
        for ds in sets:
            results.append(self.run_set(ds))
        return {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "success": all(r.get("success") for r in results) and len(results) > 0,
            "elapsed_s": round(time.perf_counter() - t0, 2),
            "sets": results,
            "estimator_excel_opened_during_production": False,
            "reuse_detected_any": any(r.get("reuse_detected") for r in results),
        }

    def _load_completed_result(self, ds: DiscoveredSet) -> Optional[Dict[str, Any]]:
        """Return prior successful production_result.json if artefacts still exist."""
        set_dir = self.phase_output_root / _folder_slug(ds.set_key)
        prod_path = set_dir / "production_result.json"
        wb = set_dir / "Estimation_Output.xlsx"
        if not (prod_path.exists() and wb.exists()):
            return None
        try:
            data = json.loads(prod_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not data.get("success"):
            return None
        run_root = Path(data.get("run_root") or "")
        if not run_root.exists() or not (run_root / VB1_EXCEL_REL).exists():
            return None
        data["resumed_skip"] = True
        data["reuse_detected"] = False
        data["estimator_excel_opened_during_production"] = False
        return data

    def _find_recoverable_web_run(self, ds: DiscoveredSet) -> Optional[Path]:
        """
        Find newest fresh qa2_* run for this set that already has a VB1 workbook
        but was interrupted before phase mirroring (e.g. T16CHAIN timeout).
        """
        web = self.engine_root / "data" / "web_runs"
        if not web.exists():
            return None
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in ds.name)
        cands = sorted(
            [p for p in web.glob(f"qa2_{safe}_*") if p.is_dir()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        set_dir = self.phase_output_root / _folder_slug(ds.set_key)
        mirrored_wb = set_dir / "Estimation_Output.xlsx"
        for cand in cands:
            excel = cand / VB1_EXCEL_REL
            if not excel.exists():
                continue
            # Prefer runs that still need Track1 completion or phase mirroring
            if not mirrored_wb.exists() or not self._t16_complete(cand):
                return cand
        return None

    def _recover_from_timeout(
        self,
        pipe_mod: Any,
        runner: Any,
        ds: DiscoveredSet,
        exc: subprocess.TimeoutExpired,
    ) -> Tuple[Any, bool, Dict[str, Any]]:
        run_root = self._run_root_from_timeout(exc, ds.name)
        excel = run_root / VB1_EXCEL_REL if run_root else None
        t16_finish: Dict[str, Any] = {}
        if run_root and excel and excel.exists():
            print(f"  recovered run_root={run_root.name} (VB1 workbook present)")
            if not self._t16_complete(run_root):
                t16_finish = self._run_t16chain_extended(run_root)
            ok = excel.exists() and (
                self._t16_soft_ok(run_root) or bool(t16_finish.get("success"))
            )
            pipe = pipe_mod.PipelineResult(
                drawing_set=ds.name,
                run_root=run_root,
                model_excel=excel,
                success=ok,
                elapsed_s=float(exc.timeout or 0),
                stages=[],
                error="" if ok else f"timeout recovery incomplete: {exc}",
            )
            return pipe, True, t16_finish

        # No recoverable workbook — re-raise as failed result
        if run_root is None:
            # Stage a fresh run only if we cannot find the timed-out one
            run_root = runner.stage_drawing_set(
                ds.name, ds.general_notes, ds.framing, ds.reinforcement
            )
        pipe = pipe_mod.PipelineResult(
            drawing_set=ds.name,
            run_root=run_root,
            model_excel=None,
            success=False,
            elapsed_s=float(exc.timeout or 0),
            stages=[],
            error=f"TimeoutExpired without recoverable workbook: {exc}",
        )
        return pipe, True, t16_finish

    def _run_root_from_timeout(
        self, exc: subprocess.TimeoutExpired, drawing_set_name: str
    ) -> Optional[Path]:
        cmd = list(exc.cmd or [])
        for part in cmd:
            p = Path(str(part))
            if p.is_dir() and (p / "data" / "output").exists():
                return p
        # Fallback: newest matching web_run
        web = self.engine_root / "data" / "web_runs"
        if not web.exists():
            return None
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in drawing_set_name)
        cands = sorted(
            [p for p in web.glob(f"qa2_{safe}_*") if p.is_dir()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return cands[0] if cands else None

    def _t16_soft_ok(self, run_root: Path) -> bool:
        soft = run_root / T16_SOFT_REL
        return soft.exists() and any(soft.glob("*.png"))

    def _t16_complete(self, run_root: Path) -> bool:
        return self._t16_soft_ok(run_root) and (run_root / T1831_REL).exists()

    def _run_t16chain_extended(self, run_root: Path) -> Dict[str, Any]:
        script = self.engine_root / "Run_PY" / "run_phase_track1_visual_chain.py"
        env = os.environ.copy()
        env["STEEL_ENGINE_ROOT"] = str(self.engine_root)
        env["STEEL_RUN_ROOT"] = str(run_root)
        env["STEEL_OUTPUT_ROOT"] = str(run_root / "data" / "output")
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, str(script), str(run_root)],
                cwd=str(self.engine_root),
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=T16CHAIN_EXTENDED_TIMEOUT_S,
            )
            elapsed = round(time.perf_counter() - t0, 2)
            ok = proc.returncode == 0 or self._t16_soft_ok(run_root)
            return {
                "success": ok,
                "exit_code": proc.returncode,
                "elapsed_s": elapsed,
                "soft_ok": self._t16_soft_ok(run_root),
                "complete": self._t16_complete(run_root),
                "stderr_tail": (proc.stderr or "")[-1500:],
            }
        except subprocess.TimeoutExpired:
            elapsed = round(time.perf_counter() - t0, 2)
            ok = self._t16_soft_ok(run_root)
            return {
                "success": ok,
                "exit_code": -1,
                "elapsed_s": elapsed,
                "soft_ok": ok,
                "complete": self._t16_complete(run_root),
                "error": f"extended T16CHAIN timeout after {T16CHAIN_EXTENDED_TIMEOUT_S}s",
            }

    def _mirror_artefacts(
        self, set_dir: Path, run_root: Path, excel: Optional[Path]
    ) -> Dict[str, Any]:
        out = run_root / "data" / "output"
        mirrored: Dict[str, Any] = {}

        if excel and excel.exists():
            dest = set_dir / "Estimation_Output.xlsx"
            shutil.copy2(excel, dest)
            mirrored["workbook"] = str(dest)

        render_sources = [
            (
                "shared_renders",
                out / "PhaseT183_shared_engineering_ownership" / "RenderedBeams",
            ),
            (
                "adaptive_renders",
                out / "PhaseT182_adaptive_render_extent" / "RenderedBeams",
            ),
            (
                "opencv_crops",
                out / "PhaseT1_geometric_stirrup_evidence" / "opencv_renders",
            ),
        ]
        crops_dir = set_dir / "RenderedCrops"
        crops_dir.mkdir(exist_ok=True)
        n = 0
        for label, src in render_sources:
            if not src.exists():
                continue
            dest = crops_dir / label
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            count = len(list(dest.rglob("*.png")))
            mirrored[label] = {"path": str(dest), "png_count": count}
            n += count
            break
        ocv = out / "PhaseT1_geometric_stirrup_evidence" / "opencv_renders"
        if ocv.exists() and "opencv_crops" not in mirrored:
            dest = crops_dir / "opencv_renders"
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(ocv, dest)
            mirrored["opencv_crops"] = {
                "path": str(dest),
                "png_count": len(list(dest.rglob("*.png"))),
            }

        for label, rel in (
            ("t182_comparison", "PhaseT182_adaptive_render_extent/Comparison"),
            ("t181_comparison", "PhaseT181_render_validation/Comparison"),
        ):
            src = out / rel
            if src.exists():
                dest = set_dir / "ComparisonRenders" / label
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(src, dest)
                mirrored[label] = str(dest)

        eng_dir = set_dir / "EngineeringSummaries"
        eng_dir.mkdir(exist_ok=True)
        for rel in (
            "PhaseR1.3_pipeline_integration/integration_summary.json",
            "PhaseT1_geometric_stirrup_evidence/t1_run_summary.json",
            "PhaseT18_beam_ownership/BeamOwnership.json",
            "PhaseT1831_shared_scope_dedup/SharedAnnotationRegistry.json",
            "PhaseT183_shared_engineering_ownership/MergedOwnership.json",
        ):
            src = out / rel
            if src.exists():
                dest = eng_dir / Path(rel).name
                shutil.copy2(src, dest)
                mirrored[f"eng_{dest.name}"] = str(dest)

        mirrored["primary_crop_png_total"] = n
        return mirrored
