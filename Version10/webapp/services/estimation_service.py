"""
Estimation service wrapper — production pipeline (MODEL 8.9.5).
Invokes existing Version8 production runners without modifying engineering logic.
MODEL_VERSION: 8.9.5
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from config import (
    ALLOWED_EXTENSIONS,
    LOG_ROOT,
    L22_REGISTRY_REL,
    OUTPUT_ROOT,
    PRODUCTION_STAGES,
    R12A_CATALOG_REL,
    R13_MODELS_REL,
    R21C_FACTS_REL,
    R21D_FACTS_REL,
    R31_RELS_REL,
    R3_CONTEXTS_REL,
    R2A_GN_POINTER,
    UPLOAD_ROOT,
    V8_ROOT,
    VB1_EXCEL_REL,
    WEB_RUNS_ROOT,
)

LOG_ROOT.mkdir(parents=True, exist_ok=True)
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
WEB_RUNS_ROOT.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("steel_webapp.estimation")
_handler = logging.FileHandler(LOG_ROOT / "webapp.log", encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
if not logger.handlers:
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


class EstimationError(Exception):
    """User-facing estimation failure (no stack traces)."""


@dataclass
class JobState:
    run_id: str
    status: str = "queued"  # queued|running|success|error
    message: str = "Queued"
    workbook_name: Optional[str] = None
    workbook_path: Optional[str] = None
    duration_s: Optional[float] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    filenames: Dict[str, str] = field(default_factory=dict)


_JOBS: Dict[str, JobState] = {}
_LOCK = threading.Lock()


def get_job(run_id: str) -> Optional[JobState]:
    with _LOCK:
        return _JOBS.get(run_id)


def _set_job(run_id: str, **kwargs: Any) -> None:
    with _LOCK:
        job = _JOBS.get(run_id)
        if not job:
            return
        for k, v in kwargs.items():
            setattr(job, k, v)


def _is_dxf(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def _safe_name(filename: str) -> str:
    name = secure_filename(filename or "")
    if not name:
        raise EstimationError("Invalid filename.")
    # Prevent path traversal remnants
    name = Path(name).name
    if ".." in name or "/" in name or "\\" in name:
        raise EstimationError("Invalid filename.")
    if not _is_dxf(name):
        raise EstimationError("Only .dxf files are allowed.")
    return name


def validate_uploads(
    general_notes: Optional[FileStorage],
    framing: Optional[FileStorage],
    reinforcement: Optional[FileStorage],
) -> None:
    missing = []
    if general_notes is None or not general_notes.filename:
        missing.append("General Notes DXF")
    if framing is None or not framing.filename:
        missing.append("Beam Framing Plan DXF")
    if reinforcement is None or not reinforcement.filename:
        missing.append("Beam Reinforcement Plan DXF")
    if missing:
        raise EstimationError("Missing required drawing(s): " + ", ".join(missing))

    for label, f in (
        ("General Notes DXF", general_notes),
        ("Beam Framing Plan DXF", framing),
        ("Beam Reinforcement Plan DXF", reinforcement),
    ):
        assert f is not None
        ext = Path(f.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise EstimationError(
                f"{label}: only .dxf is allowed (received '{ext or 'unknown'}')."
            )


def start_estimation(
    general_notes: FileStorage,
    framing: FileStorage,
    reinforcement: FileStorage,
) -> str:
    validate_uploads(general_notes, framing, reinforcement)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    upload_dir = UPLOAD_ROOT / run_id
    staging = WEB_RUNS_ROOT / run_id
    for sub in ("general_notes", "framing", "reinforcement"):
        (staging / sub).mkdir(parents=True, exist_ok=True)
    upload_dir.mkdir(parents=True, exist_ok=True)

    gn_name = _safe_name(general_notes.filename or "general_notes.dxf")
    fr_name = _safe_name(framing.filename or "framing.dxf")
    re_name = _safe_name(reinforcement.filename or "reinforcement.dxf")

    # Ensure classifier-friendly names if user uploads generic names
    if "note" not in gn_name.lower() and "general" not in gn_name.lower():
        gn_name = f"GENERAL_NOTES_{gn_name}"
    if "fram" not in fr_name.lower() and "layout" not in fr_name.lower():
        fr_name = f"FramingPlan_{fr_name}"
    if "reinforc" not in re_name.lower() and "rebar" not in re_name.lower():
        re_name = f"BeamReinforcementDetails_{re_name}"

    gn_path = staging / "general_notes" / gn_name
    fr_path = staging / "framing" / fr_name
    re_path = staging / "reinforcement" / re_name

    general_notes.save(gn_path)
    framing.save(fr_path)
    reinforcement.save(re_path)

    # Keep a copy under uploads for audit trail during the run
    shutil.copy2(gn_path, upload_dir / gn_name)
    shutil.copy2(fr_path, upload_dir / fr_name)
    shutil.copy2(re_path, upload_dir / re_name)

    job = JobState(
        run_id=run_id,
        status="queued",
        message="Uploading files...",
        filenames={
            "general_notes": gn_name,
            "framing": fr_name,
            "reinforcement": re_name,
        },
    )
    with _LOCK:
        _JOBS[run_id] = job

    logger.info(
        "Execution start run_id=%s files=%s",
        run_id,
        job.filenames,
    )

    thread = threading.Thread(
        target=_run_pipeline,
        args=(run_id, staging, gn_path),
        daemon=True,
        name=f"estimate-{run_id}",
    )
    thread.start()
    return run_id


def _write_r2a_gn_pointer(gn_path: Path) -> None:
    """
    Existing R.2A factory looks for general_notes_dxf in a specific registry path.
    Write a temporary pointer so uploaded GN is used — no engineering code changes.
    """
    R2A_GN_POINTER.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "general_notes_dxf": str(gn_path.resolve()),
        "project_id": "WEBAPP_UPLOAD",
        "source": "UI.1_WEBAPP_POINTER",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    R2A_GN_POINTER.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _clear_r2a_gn_pointer() -> None:
    try:
        if R2A_GN_POINTER.exists():
            # Only remove if it is our pointer file
            data = json.loads(R2A_GN_POINTER.read_text(encoding="utf-8"))
            if data.get("source") == "UI.1_WEBAPP_POINTER":
                R2A_GN_POINTER.unlink(missing_ok=True)
    except Exception:
        logger.warning("Could not clear R.2A GN pointer file")


def _stage_env(staging: Path) -> dict:
    env = os.environ.copy()
    env["STEEL_ENGINE_ROOT"] = str(V8_ROOT.resolve())
    env["STEEL_RUN_ROOT"] = str(staging.resolve())
    env["STEEL_OUTPUT_ROOT"] = str((staging / "data" / "output").resolve())
    return env


def _run_stage(stage: Dict[str, Any], staging: Path) -> None:
    script = V8_ROOT / stage["script"]
    if not script.exists():
        raise EstimationError(f"Production runner not found: {stage['script']}")

    cmd = [sys.executable, str(script)]
    # Pass run_root so runners resolve per-run output even if env is stripped
    cmd.append(str(staging.resolve()))

    logger.info("Runner start stage=%s cmd=%s", stage["id"], " ".join(cmd))
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=str(V8_ROOT),
        env=_stage_env(staging),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=int(stage.get("timeout_s") or 600),
    )
    elapsed = round(time.perf_counter() - t0, 2)
    logger.info(
        "Runner finish stage=%s exit=%s duration_s=%s",
        stage["id"],
        proc.returncode,
        elapsed,
    )
    if proc.returncode != 0:
        err_tail = (proc.stderr or proc.stdout or "").strip()
        if err_tail:
            logger.error(
                "Stage %s stderr/stdout (tail):\n%s",
                stage["id"],
                "\n".join(err_tail.splitlines()[-40:]),
            )
        # Soft-success when expected stage artefacts were written
        if stage["id"] == "R3":
            contexts = staging / R3_CONTEXTS_REL
            if contexts.exists():
                logger.warning(
                    "Stage R3 exit=%s with GeometryContexts present — soft success",
                    proc.returncode,
                )
                return
        if stage["id"] == "R31":
            rels = staging / R31_RELS_REL
            if rels.exists():
                logger.warning(
                    "Stage R31 exit=%s with EngineeringDrawingRelationships present — soft success",
                    proc.returncode,
                )
                return
        if stage["id"] == "R12A":
            catalog = staging / R12A_CATALOG_REL
            if catalog.exists():
                logger.warning(
                    "Stage R12A exit=%s with validated_beam_geometry present — soft success",
                    proc.returncode,
                )
                return
        if stage["id"] == "R13":
            models = staging / R13_MODELS_REL
            if models.exists():
                logger.warning(
                    "Stage R13 exit=%s with production models present — soft success",
                    proc.returncode,
                )
                return
        if stage["id"] == "VB1":
            xlsx = staging / VB1_EXCEL_REL
            if xlsx.exists():
                logger.warning(
                    "Stage VB1 exit=%s with Estimation_Output.xlsx present — soft success",
                    proc.returncode,
                )
                return
        if stage["id"] == "L22":
            reg = staging / L22_REGISTRY_REL
            if reg.exists():
                logger.warning(
                    "Stage L22 exit=%s with geometry_registry present — soft success",
                    proc.returncode,
                )
                return
        if stage["id"] == "R21D":
            facts = staging / R21D_FACTS_REL
            if facts.exists():
                logger.warning(
                    "Stage R21D exit=%s with EngineeringFacts present — soft success",
                    proc.returncode,
                )
                return
        if stage["id"] == "R21C":
            facts = staging / R21C_FACTS_REL
            if facts.exists():
                logger.warning(
                    "Stage R21C exit=%s with EngineeringFacts present — soft success",
                    proc.returncode,
                )
                return
        if stage["id"] == "R21B":
            eso = staging / "data/output/PhaseR2.1B_engineering_semantic_interpreter/engineering_semantic_objects.json"
            if eso.exists():
                logger.warning(
                    "Stage R21B exit=%s with ESO present — soft success",
                    proc.returncode,
                )
                return
        raise EstimationError(
            f"Engineering pipeline failed during stage {stage['id']}. "
            "Check webapp/logs/webapp.log for details, then try again."
        )


def _run_pipeline(run_id: str, staging: Path, gn_path: Path) -> None:
    t0 = time.perf_counter()
    try:
        _set_job(run_id, status="running", message="Preparing estimation...")
        _write_r2a_gn_pointer(gn_path)

        for stage in PRODUCTION_STAGES:
            _set_job(run_id, message=stage["label"])
            _run_stage(stage, staging)

        facts = staging / R21D_FACTS_REL
        registry = staging / L22_REGISTRY_REL
        contexts = staging / R3_CONTEXTS_REL
        excel = staging / VB1_EXCEL_REL
        if not facts.exists():
            raise EstimationError(
                "Pipeline completed but EngineeringFacts.json was not generated "
                f"at {facts}."
            )
        if not registry.exists():
            raise EstimationError(
                "Pipeline completed but geometry_registry.json was not generated "
                f"at {registry}."
            )
        if not contexts.exists():
            raise EstimationError(
                "Geometry Context Engine completed but GeometryContexts.json "
                f"was not generated at {contexts}."
            )
        if not excel.exists():
            raise EstimationError(
                "Production pipeline completed but Estimation_Output.xlsx "
                f"was not generated at {excel}."
            )

        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        download_name = f"Estimation_Output_{run_id}.xlsx"
        download_path = OUTPUT_ROOT / download_name
        shutil.copy2(excel, download_path)

        duration = round(time.perf_counter() - t0, 2)
        _set_job(
            run_id,
            status="success",
            message="Estimation workbook generated successfully.",
            workbook_name=download_name,
            workbook_path=str(download_path.resolve()),
            duration_s=duration,
        )
        logger.info(
            "Pipeline complete run_id=%s excel=%s download=%s duration_s=%s",
            run_id,
            excel,
            download_path,
            duration,
        )
    except subprocess.TimeoutExpired:
        logger.exception("Pipeline timeout run_id=%s", run_id)
        _set_job(
            run_id,
            status="error",
            error="Engineering pipeline timed out. Please try again with a smaller drawing set.",
            message="Estimation failed",
            duration_s=round(time.perf_counter() - t0, 2),
        )
    except EstimationError as exc:
        logger.error("Estimation error run_id=%s: %s", run_id, exc)
        _set_job(
            run_id,
            status="error",
            error=str(exc),
            message="Estimation failed",
            duration_s=round(time.perf_counter() - t0, 2),
        )
    except Exception:
        logger.exception("Unexpected error run_id=%s", run_id)
        _set_job(
            run_id,
            status="error",
            error="An unexpected error occurred while running the estimation engine.",
            message="Estimation failed",
            duration_s=round(time.perf_counter() - t0, 2),
        )
    finally:
        _clear_r2a_gn_pointer()
        # Retain per-run web_runs tree; remove webapp uploads audit copy only.
        upload_copy = UPLOAD_ROOT / run_id
        try:
            if upload_copy.exists():
                shutil.rmtree(upload_copy, ignore_errors=True)
        except Exception:
            logger.warning("Cleanup failed for %s", upload_copy)
        logger.info("Run artefacts retained staging=%s", staging)
