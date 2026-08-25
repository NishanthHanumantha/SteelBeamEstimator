"""
Flask estimation service — Version10 web adapter wrapper (Phase W.2).

Uploads, job state, single-flight, and download naming live here.
Engineering execution is delegated to version10_adapter.
"""
from __future__ import annotations

import logging
import shutil
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

import config
from services.flight_guard import GUARD
from services.hybrid_shadow_service import maybe_run_hybrid_shadow
from services.version10_adapter import AdapterError, invoke_version10_pipeline

config.LOG_ROOT.mkdir(parents=True, exist_ok=True)
config.UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
config.OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
config.WEB_RUNS_ROOT.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("steel_webapp.estimation")
_handler = logging.FileHandler(config.LOG_ROOT / "webapp.log", encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
if not logger.handlers:
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


class EstimationError(Exception):
    """User-facing estimation failure (no stack traces)."""


class EstimationBusyError(EstimationError):
    """Single-flight rejection."""


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
    summary: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    stages_run: List[str] = field(default_factory=list)
    t1_executed: bool = False
    engine_root: str = ""
    hybrid_summary: Dict[str, Any] = field(default_factory=dict)


_JOBS: Dict[str, JobState] = {}
_LOCK = threading.Lock()


def get_job(run_id: str) -> Optional[JobState]:
    with _LOCK:
        return _JOBS.get(run_id)


def active_run_id() -> Optional[str]:
    return GUARD.active_run_id()


def _set_job(run_id: str, **kwargs: Any) -> None:
    with _LOCK:
        job = _JOBS.get(run_id)
        if not job:
            return
        for k, v in kwargs.items():
            setattr(job, k, v)


def _is_dxf(filename: str) -> bool:
    return Path(filename).suffix.lower() in config.ALLOWED_EXTENSIONS


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


def _stream_size(storage: FileStorage) -> int:
    stream = storage.stream
    try:
        pos = stream.tell()
    except Exception:
        pos = 0
    try:
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(0)
        return int(size)
    except Exception:
        try:
            stream.seek(pos)
        except Exception:
            pass
        data = storage.read()
        try:
            stream.seek(0)
        except Exception:
            pass
        return len(data or b"")


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
        if ext not in config.ALLOWED_EXTENSIONS:
            raise EstimationError(
                f"{label}: only .dxf is allowed (received '{ext or 'unknown'}')."
            )
        size = _stream_size(f)
        if size <= 0:
            raise EstimationError(f"{label} is empty.")
        if size < config.MIN_DXF_BYTES:
            raise EstimationError(
                f"{label} is too small to be a valid DXF drawing."
            )


def start_estimation(
    general_notes: FileStorage,
    framing: FileStorage,
    reinforcement: FileStorage,
) -> str:
    validate_uploads(general_notes, framing, reinforcement)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    if not GUARD.acquire(run_id):
        logger.info(
            "Single-flight reject run_id=%s active=%s",
            run_id,
            GUARD.active_run_id(),
        )
        raise EstimationBusyError(config.BUSY_MESSAGE)

    upload_dir = config.UPLOAD_ROOT / run_id
    staging = config.WEB_RUNS_ROOT / run_id
    try:
        for sub in ("general_notes", "framing", "reinforcement"):
            (staging / sub).mkdir(parents=True, exist_ok=True)
        (staging / "data" / "output").mkdir(parents=True, exist_ok=True)
        (staging / "logs").mkdir(parents=True, exist_ok=True)
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

        general_notes.save(gn_path)
        framing.save(fr_path)
        reinforcement.save(re_path)

        for label, path in (
            ("General Notes DXF", gn_path),
            ("Beam Framing Plan DXF", fr_path),
            ("Beam Reinforcement Plan DXF", re_path),
        ):
            if not path.exists() or path.stat().st_size < config.MIN_DXF_BYTES:
                raise EstimationError(f"{label} is empty or could not be saved.")

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
            engine_root=str(config.ENGINE_ROOT.resolve()),
        )
        with _LOCK:
            _JOBS[run_id] = job

        logger.info(
            "Execution start run_id=%s files=%s engine_root=%s",
            run_id,
            job.filenames,
            job.engine_root,
        )

        thread = threading.Thread(
            target=_run_pipeline,
            args=(run_id, staging, gn_path),
            daemon=True,
            name=f"estimate-{run_id}",
        )
        thread.start()
        return run_id
    except Exception:
        GUARD.release(run_id)
        raise


def _run_pipeline(run_id: str, staging: Path, gn_path: Path) -> None:
    hybrid_cfg = None
    try:
        from PhaseW5_production_hybrid_shadow.settings import load_settings as _load_hybrid

        hybrid_cfg = _load_hybrid()
    except Exception:
        hybrid_cfg = None
    try:
        _set_job(run_id, status="running", message="Preparing estimation...")

        def on_stage(_stage_id: str, label: str) -> None:
            _set_job(run_id, message=label)

        result = invoke_version10_pipeline(
            run_id=run_id,
            staging=staging,
            gn_path=gn_path,
            on_stage=on_stage,
        )
        if not result.success or not result.output_path:
            raise EstimationError(
                result.error or "Engineering pipeline failed to produce a workbook."
            )

        excel = Path(result.output_path)
        if not excel.exists():
            raise EstimationError(
                "Production pipeline completed but Estimation_Output.xlsx "
                f"was not generated at {excel}."
            )

        config.OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        download_name = f"Estimation_Output_{run_id}.xlsx"
        download_path = config.OUTPUT_ROOT / download_name
        shutil.copy2(excel, download_path)

        pending_hybrid = None
        if (
            hybrid_cfg is not None
            and hybrid_cfg.mode != "off"
            and not config.hybrid_stage_configured()
        ):
            pending_hybrid = {
                "hybrid_mode": hybrid_cfg.mode,
                "hybrid_status": "PENDING",
                "reason": "SHADOW_AFTER_EXCEL",
                "request_count": 0,
            }
            _set_job(run_id, hybrid_summary=pending_hybrid)

        hybrid_summary = maybe_run_hybrid_shadow(
            run_id=run_id,
            staging=staging,
            settings=hybrid_cfg,
        )
        _set_job(
            run_id,
            status="success",
            message="Estimation workbook generated successfully.",
            workbook_name=download_name,
            workbook_path=str(download_path.resolve()),
            duration_s=result.duration_s,
            summary=result.summary,
            warnings=result.warnings,
            stages_run=result.stages_run,
            t1_executed=result.t1_executed,
            engine_root=result.engine_root,
            hybrid_summary=hybrid_summary or pending_hybrid or {},
        )
        logger.info(
            "Pipeline complete run_id=%s excel=%s download=%s duration_s=%s "
            "t1_executed=%s stages=%s",
            run_id,
            excel,
            download_path,
            result.duration_s,
            result.t1_executed,
            result.stages_run,
        )
    except AdapterError as exc:
        logger.error("Adapter error run_id=%s: %s", run_id, exc)
        _set_job(
            run_id,
            status="error",
            error=str(exc),
            message="Estimation failed",
        )
    except EstimationError as exc:
        logger.error("Estimation error run_id=%s: %s", run_id, exc)
        _set_job(
            run_id,
            status="error",
            error=str(exc),
            message="Estimation failed",
        )
    except Exception:
        logger.exception("Unexpected error run_id=%s", run_id)
        _set_job(
            run_id,
            status="error",
            error="An unexpected error occurred while running the estimation engine.",
            message="Estimation failed",
        )
    finally:
        GUARD.release(run_id)
        upload_copy = config.UPLOAD_ROOT / run_id
        try:
            if upload_copy.exists():
                shutil.rmtree(upload_copy, ignore_errors=True)
        except Exception:
            logger.warning("Cleanup failed for %s", upload_copy)
        logger.info("Run artefacts retained staging=%s", staging)
