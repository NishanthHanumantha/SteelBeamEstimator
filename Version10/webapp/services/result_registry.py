"""
Phase W.12 — durable run-isolated result registry.

Excel copies under OUTPUT_ROOT are the downloadable artefact.
A JSON manifest under the run tree is the source of truth after worker restart.
Never stores secrets. Public APIs must not receive absolute filesystem paths.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import config

logger = logging.getLogger("steel_webapp.result_registry")

SCHEMA = "w12_result_manifest_v1"
MANIFEST_NAME = "result_manifest.json"
RUN_ID_RE = re.compile(r"^[0-9]{8}_[0-9]{6}_[0-9a-f]{8}$")

LIFECYCLE_PROCESSING = "PROCESSING"
LIFECYCLE_EXCEL_GENERATED = "EXCEL_GENERATED"
LIFECYCLE_RESULT_REGISTERED = "RESULT_REGISTERED"
LIFECYCLE_DOWNLOAD_READY = "DOWNLOAD_READY"
LIFECYCLE_FAILED = "FAILED"
LIFECYCLE_RESULT_UNAVAILABLE = "RESULT_UNAVAILABLE"
LIFECYCLE_INTERRUPTED = "PROCESSING_INTERRUPTED"

CLASS_OK = "OK"
CLASS_INVALID_RUN = "INVALID_RUN"
CLASS_NOT_READY = "WORKBOOK_NOT_READY"
CLASS_UNAVAILABLE = "RESULT_UNAVAILABLE"
CLASS_INTERRUPTED = "PROCESSING_INTERRUPTED"
CLASS_TRAVERSAL = "PATH_REJECTED"


def is_valid_run_id(run_id: str) -> bool:
    return bool(run_id) and bool(RUN_ID_RE.fullmatch(str(run_id)))


def manifest_path(run_id: str) -> Path:
    return config.WEB_RUNS_ROOT / run_id / MANIFEST_NAME


def workbook_filename(run_id: str) -> str:
    return f"Estimation_Output_{run_id}.xlsx"


def workbook_path_for_run(run_id: str) -> Optional[Path]:
    """Return the canonical download path, or None if run_id is unsafe."""
    if not is_valid_run_id(run_id):
        return None
    root = config.OUTPUT_ROOT.resolve()
    path = (config.OUTPUT_ROOT / workbook_filename(run_id)).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path


def workbook_is_present(run_id: str) -> bool:
    path = workbook_path_for_run(run_id)
    if path is None or not path.is_file():
        return False
    try:
        return path.stat().st_size > 0
    except OSError:
        return False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_manifest(run_id: str) -> Optional[Dict[str, Any]]:
    if not is_valid_run_id(run_id):
        return None
    path = manifest_path(run_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("result manifest unreadable run_id=%s", run_id)
        return None
    return data if isinstance(data, dict) else None


def update_manifest(run_id: str, **fields: Any) -> Dict[str, Any]:
    if not is_valid_run_id(run_id):
        return {}
    data = load_manifest(run_id) or {
        "schema": SCHEMA,
        "run_id": run_id,
    }
    data["schema"] = SCHEMA
    data["run_id"] = run_id
    for key, value in fields.items():
        if value is not None:
            data[key] = value
    data["updated_at"] = _now()
    _atomic_write(manifest_path(run_id), data)
    return data


def write_processing_manifest(run_id: str, filenames: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    return update_manifest(
        run_id,
        lifecycle=LIFECYCLE_PROCESSING,
        pipeline_status="running",
        excel_generated=False,
        result_registered=False,
        download_ready=False,
        workbook_name=workbook_filename(run_id),
        output_class="webapp_outputs",
        filenames=filenames or {},
        created_at=_now(),
        download_attempts=0,
        last_download_classification=None,
    )


def mark_excel_generated(run_id: str, byte_size: int) -> Dict[str, Any]:
    return update_manifest(
        run_id,
        lifecycle=LIFECYCLE_EXCEL_GENERATED,
        excel_generated=True,
        excel_byte_size=int(byte_size),
        download_ready=False,
        result_registered=False,
    )


def register_download_ready(
    run_id: str,
    *,
    duration_s: Optional[float] = None,
    summary: Optional[Dict[str, Any]] = None,
    warnings: Optional[list] = None,
    stages_run: Optional[list] = None,
    t1_executed: bool = False,
    hybrid_summary: Optional[Dict[str, Any]] = None,
    filenames: Optional[Dict[str, str]] = None,
    engine_label: str = "Version10",
) -> Dict[str, Any]:
    """EXCEL_GENERATED is not DOWNLOAD_READY. Registration requires the file to exist."""
    path = workbook_path_for_run(run_id)
    if path is None or not path.is_file() or path.stat().st_size <= 0:
        raise FileNotFoundError("excel_missing")
    return update_manifest(
        run_id,
        lifecycle=LIFECYCLE_DOWNLOAD_READY,
        pipeline_status="success",
        excel_generated=True,
        result_registered=True,
        download_ready=True,
        workbook_name=path.name,
        output_class="webapp_outputs",
        excel_byte_size=int(path.stat().st_size),
        duration_s=duration_s,
        summary=summary or {},
        warnings=warnings or [],
        stages_run=stages_run or [],
        t1_executed=bool(t1_executed),
        hybrid_summary=hybrid_summary or {},
        filenames=filenames or {},
        engine_label=engine_label,
        registered_at=_now(),
    )


def register_existing_workbook(
    run_id: str,
    prior: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Recover DOWNLOAD_READY from a surviving Excel copy (worker restart / pre-W.12)."""
    path = workbook_path_for_run(run_id)
    if path is None or not path.is_file():
        raise FileNotFoundError("excel_missing")
    prior = prior or {}
    return update_manifest(
        run_id,
        lifecycle=LIFECYCLE_DOWNLOAD_READY,
        pipeline_status="success",
        excel_generated=True,
        result_registered=True,
        download_ready=True,
        workbook_name=path.name,
        output_class="webapp_outputs",
        excel_byte_size=int(path.stat().st_size),
        duration_s=prior.get("duration_s"),
        summary=prior.get("summary") or {},
        warnings=prior.get("warnings") or [],
        stages_run=prior.get("stages_run") or [],
        t1_executed=bool(prior.get("t1_executed")),
        hybrid_summary=prior.get("hybrid_summary") or {},
        filenames=prior.get("filenames") or {},
        recovered=True,
        registered_at=prior.get("registered_at") or _now(),
    )


def mark_failed(run_id: str, error: str) -> Dict[str, Any]:
    return update_manifest(
        run_id,
        lifecycle=LIFECYCLE_FAILED,
        pipeline_status="error",
        download_ready=False,
        result_registered=False,
        error=error,
    )


def mark_interrupted(run_id: str) -> Dict[str, Any]:
    return update_manifest(
        run_id,
        lifecycle=LIFECYCLE_INTERRUPTED,
        pipeline_status="error",
        download_ready=False,
        error=(
            "Estimation was interrupted, likely because the server restarted. "
            "Please start a new estimation."
        ),
        classification=CLASS_INTERRUPTED,
    )


def record_download_attempt(
    run_id: str,
    *,
    http_status: int,
    classification: str,
    ok: bool,
) -> None:
    try:
        data = load_manifest(run_id) or {"schema": SCHEMA, "run_id": run_id}
        attempts = int(data.get("download_attempts") or 0) + 1
        update_manifest(
            run_id,
            download_attempts=attempts,
            last_download_at=_now(),
            last_download_http_status=int(http_status),
            last_download_classification=classification,
            last_download_ok=bool(ok),
        )
    except Exception:
        logger.warning("download attempt log failed run_id=%s", run_id)


def public_lifecycle(run_id: str, job_status: str, download_ready: bool, excel_exists: bool) -> str:
    if job_status == "error":
        return LIFECYCLE_FAILED
    if job_status in {"queued", "running"}:
        return LIFECYCLE_PROCESSING
    if job_status == "success" and download_ready and excel_exists:
        return LIFECYCLE_DOWNLOAD_READY
    if job_status == "success" and not excel_exists:
        return LIFECYCLE_RESULT_UNAVAILABLE
    if job_status == "success":
        return LIFECYCLE_RESULT_REGISTERED
    return LIFECYCLE_PROCESSING


def resolve_download(run_id: str) -> Tuple[str, Optional[Path], str]:
    """
    Return (classification, path, error_message).
    Path is only set on CLASS_OK. Never follows caller-supplied filesystem paths.
    """
    if not is_valid_run_id(run_id):
        return CLASS_INVALID_RUN, None, "Unknown run id."
    path = workbook_path_for_run(run_id)
    if path is None:
        return CLASS_TRAVERSAL, None, "Unknown run id."
    manifest = load_manifest(run_id)
    present = path.is_file() and path.stat().st_size > 0
    lifecycle = (manifest or {}).get("lifecycle")
    pipeline = (manifest or {}).get("pipeline_status")
    if present and lifecycle in {None, LIFECYCLE_EXCEL_GENERATED, LIFECYCLE_RESULT_REGISTERED, LIFECYCLE_PROCESSING}:
        try:
            register_existing_workbook(run_id, manifest)
            lifecycle = LIFECYCLE_DOWNLOAD_READY
        except Exception:
            logger.warning("legacy excel recover failed run_id=%s", run_id)
    if present and (lifecycle == LIFECYCLE_DOWNLOAD_READY or pipeline == "success" or manifest is None):
        return CLASS_OK, path, ""
    if lifecycle == LIFECYCLE_DOWNLOAD_READY and not present:
        return CLASS_UNAVAILABLE, None, (
            "The estimation completed but the workbook is no longer available."
        )
    if lifecycle in {LIFECYCLE_FAILED, LIFECYCLE_INTERRUPTED}:
        return CLASS_NOT_READY, None, "Workbook is not ready for download."
    if not present:
        return CLASS_NOT_READY, None, "Workbook is not ready for download."
    return CLASS_OK, path, ""
