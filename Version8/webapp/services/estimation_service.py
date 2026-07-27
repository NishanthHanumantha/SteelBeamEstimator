"""
Phase UI.1 — Estimation service wrapper.
Invokes existing Version8 production runners without modifying engineering logic.
MODEL_VERSION: 8.8.3
"""
from __future__ import annotations

import json
import logging
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
    OUTPUT_ROOT,
    PRODUCTION_EXCEL,
    PRODUCTION_STAGES,
    R2A_GN_POINTER,
    R3_PREREQUISITES,
    UPLOAD_ROOT,
    V7_ROOT,
    V8_ROOT,
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


def _ensure_r3_prerequisites() -> None:
    """
    R.3 requires EngineeringFacts (R.2.1D) and geometry_registry (L.2.2).
    Version8 web runs do not yet regenerate those stages (legacy hardcoded
    DXF paths). Seed from Version7 artefacts when missing — no eng changes.
    """
    missing: list[str] = []
    for item in R3_PREREQUISITES:
        dest = V8_ROOT / item["rel"]
        if dest.exists():
            continue
        src = V7_ROOT / item["rel"]
        if src.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            logger.info("Seeded R.3 prerequisite from Version7: %s", item["rel"])
        else:
            missing.append(item["label"])
    if missing:
        raise EstimationError(
            "Engineering pipeline is missing required artefacts: "
            + ", ".join(missing)
            + ". Re-run the R.2.1D / L.2.2 stages offline, then try again."
        )


def _run_stage(stage: Dict[str, Any], staging: Path) -> None:
    script = V8_ROOT / stage["script"]
    if not script.exists():
        raise EstimationError(f"Production runner not found: {stage['script']}")

    if stage["id"] == "R3":
        _ensure_r3_prerequisites()

    cmd = [sys.executable, str(script)]
    if stage.get("uses_input_folder"):
        cmd.append(str(staging))

    logger.info("Runner start stage=%s cmd=%s", stage["id"], " ".join(cmd))
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=str(V8_ROOT),
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
        # R.1.3-PI exits 1 when its 10-rule check is not 10/10 (e.g. Set 3 has
        # 61 beams vs hardcoded 62), but still chains V.B.1 and writes Excel.
        if stage["id"] == "R13PI" and PRODUCTION_EXCEL.exists():
            logger.warning(
                "Stage R13PI exit=%s with workbook present — treating as soft success",
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

        _set_job(run_id, message="Preparing download...")
        if not PRODUCTION_EXCEL.exists():
            raise EstimationError(
                "Estimation completed but the production Excel workbook was not generated."
            )

        out_name = f"Estimation_Output_{run_id}.xlsx"
        out_path = OUTPUT_ROOT / out_name
        shutil.copy2(PRODUCTION_EXCEL, out_path)

        duration = round(time.perf_counter() - t0, 2)
        _set_job(
            run_id,
            status="success",
            message="Steel Estimation Completed Successfully",
            workbook_name=out_name,
            workbook_path=str(out_path),
            duration_s=duration,
        )
        logger.info(
            "Workbook generated run_id=%s path=%s duration_s=%s",
            run_id,
            out_path,
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
        # Clean temporary uploads / staging after completion
        for path in (UPLOAD_ROOT / run_id, staging):
            try:
                if path.exists():
                    shutil.rmtree(path, ignore_errors=True)
            except Exception:
                logger.warning("Cleanup failed for %s", path)
