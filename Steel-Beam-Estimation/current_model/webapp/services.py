"""
Estimation service wrapper — Phase D.5.4.

Invokes existing production runners under ENGINE_ROOT via subprocess.
Does not modify engineering / estimation logic.
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

from config.settings import (
    ALLOWED_EXTENSIONS,
    ENGINE_ROOT,
    KEEP_WEB_RUNS,
    L22_REGISTRY_REL,
    PRODUCTION_STAGES,
    R21C_FACTS_REL,
    R21D_FACTS_REL,
    R3_CONTEXTS_REL,
    R2A_GN_POINTER,
    UPLOAD_FOLDER,
    WEB_RUNS_ROOT,
    ezdxf_is_available,
)
from config.paths import ensure_runtime_dirs

ensure_runtime_dirs()
WEB_RUNS_ROOT.mkdir(parents=True, exist_ok=True)
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("steel_beam.estimation")


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
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
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
    if not (ENGINE_ROOT / "Run_PY").is_dir():
        raise EstimationError(
            "Estimation engine is not configured. Set STEEL_ENGINE_ROOT "
            "or package runners under current_model/Run_PY."
        )
    if not ezdxf_is_available():
        raise EstimationError(
            "DXF parser dependency 'ezdxf' is not installed in the application "
            "virtualenv. On the server run: "
            f"'{sys.executable} -m pip install -r "
            f"{ENGINE_ROOT / 'requirements.txt'}' "
            "then restart the service."
        )

    validate_uploads(general_notes, framing, reinforcement)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    # Absolute paths — required under gunicorn (cwd is current_model, not Version8)
    upload_dir = (UPLOAD_FOLDER / run_id).resolve()
    staging = (WEB_RUNS_ROOT / run_id).resolve()
    for sub in ("general_notes", "framing", "reinforcement"):
        (staging / sub).mkdir(parents=True, exist_ok=True)
    upload_dir.mkdir(parents=True, exist_ok=True)

    gn_name = _safe_name(general_notes.filename or "general_notes.dxf")
    fr_name = _safe_name(framing.filename or "framing.dxf")
    re_name = _safe_name(reinforcement.filename or "reinforcement.dxf")

    if "note" not in gn_name.lower() and "general" not in gn_name.lower():
        gn_name = f"GENERAL_NOTES_{gn_name}"
    if "fram" not in fr_name.lower() and "layout" not in fr_name.lower():
        fr_name = f"FramingPlan_{fr_name}"
    if "reinforc" not in re_name.lower() and "rebar" not in re_name.lower():
        re_name = f"BeamReinforcementDetails_{re_name}"

    gn_path = staging / "general_notes" / gn_name
    fr_path = staging / "framing" / fr_name
    re_path = staging / "reinforcement" / re_name

    general_notes.save(str(gn_path))
    framing.save(str(fr_path))
    reinforcement.save(str(re_path))

    for label, path in (
        ("General Notes", gn_path),
        ("Beam Framing Plan", fr_path),
        ("Beam Reinforcement Plan", re_path),
    ):
        if not path.is_file() or path.stat().st_size <= 0:
            raise EstimationError(
                f"{label} upload was not saved to disk (empty or missing). "
                f"Expected path: {path}"
            )

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
        "Upload received run_id=%s engine_root=%s staging=%s upload_dir=%s files=%s sizes=%s",
        run_id,
        ENGINE_ROOT,
        staging,
        upload_dir,
        job.filenames,
        {
            "general_notes": gn_path.stat().st_size,
            "framing": fr_path.stat().st_size,
            "reinforcement": re_path.stat().st_size,
        },
    )
    logger.info("Processing started run_id=%s", run_id)

    thread = threading.Thread(
        target=_run_pipeline,
        args=(run_id, staging, gn_path),
        daemon=True,
        name=f"estimate-{run_id}",
    )
    thread.start()
    return run_id


def _write_r2a_gn_pointer(gn_path: Path) -> None:
    R2A_GN_POINTER.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "general_notes_dxf": str(gn_path.resolve()),
        "project_id": "WEBAPP_UPLOAD",
        "source": "D2_WEBAPP_POINTER",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    R2A_GN_POINTER.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _clear_r2a_gn_pointer() -> None:
    try:
        if R2A_GN_POINTER.exists():
            data = json.loads(R2A_GN_POINTER.read_text(encoding="utf-8"))
            if data.get("source") == "D2_WEBAPP_POINTER":
                R2A_GN_POINTER.unlink(missing_ok=True)
    except Exception:
        logger.warning("Could not clear R.2A GN pointer file")


def _ensure_r3_prerequisites() -> None:
    """Removed from D.5.1 hot path — R.3 is not in PRODUCTION_STAGES."""
    return


def _stage_env(staging: Path) -> dict:
    env = os.environ.copy()
    env["STEEL_ENGINE_ROOT"] = str(ENGINE_ROOT.resolve())
    env["STEEL_RUN_ROOT"] = str(staging.resolve())
    env["STEEL_OUTPUT_ROOT"] = str((staging / "data" / "output").resolve())
    return env


def _run_stage(stage: Dict[str, Any], staging: Path) -> None:
    script = ENGINE_ROOT / stage["script"]
    if not script.exists():
        raise EstimationError(f"Production runner not found: {stage['script']}")

    staging_abs = staging.resolve()
    cmd = [sys.executable, str(script), str(staging_abs)]

    logger.info(
        "Runner start stage=%s cwd=%s run_root=%s",
        stage["id"],
        ENGINE_ROOT,
        staging_abs,
    )
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=str(ENGINE_ROOT),
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
        if stage["id"] == "R3":
            contexts = staging / R3_CONTEXTS_REL
            if contexts.exists():
                logger.warning(
                    "Stage R3 exit=%s with GeometryContexts present — soft success",
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
            "Check logs/application.log for details, then try again."
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

        duration = round(time.perf_counter() - t0, 2)
        _set_job(
            run_id,
            status="success",
            message=(
                "Geometry Context Engine completed (through R.3). "
                "Excel workbook generation arrives in a later phase."
            ),
            workbook_name=None,
            workbook_path=None,
            duration_s=duration,
        )
        logger.info(
            "D.5.4 R.3 complete run_id=%s facts=%s registry=%s contexts=%s duration_s=%s",
            run_id,
            facts,
            registry,
            contexts,
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
        # Always keep per-run web_runs tree for D.5.1 inspection.
        upload_copy = UPLOAD_FOLDER / run_id
        try:
            if upload_copy.exists() and not KEEP_WEB_RUNS:
                shutil.rmtree(upload_copy, ignore_errors=True)
        except Exception:
            logger.warning("Cleanup failed for %s", upload_copy)
        logger.info(
            "Keeping run tree staging=%s (D.5.1 per-run artefacts)",
            staging,
        )
