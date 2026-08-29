"""Flask routes — Version10 web adapter (Phase W.2 / W.12)."""
from __future__ import annotations

import json
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
    send_file,
)

import config
from services.estimation_service import (
    EstimationBusyError,
    EstimationError,
    active_run_id,
    get_job,
    start_estimation,
)
from services.result_registry import (
    CLASS_INVALID_RUN,
    CLASS_NOT_READY,
    CLASS_OK,
    CLASS_TRAVERSAL,
    CLASS_UNAVAILABLE,
    is_valid_run_id,
    record_download_attempt,
    resolve_download,
    workbook_filename,
)

bp = Blueprint("ui", __name__)


def _load_hybrid_progress(run_id: str):
    rel = getattr(
        config,
        "W11_PROGRESS_REL",
        "data/output/PhaseW6_hybrid_semantic_resolution/hybrid_progress.json",
    )
    path = config.WEB_RUNS_ROOT / run_id / rel
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _elapsed_s(created_at):
    if not created_at:
        return None
    try:
        created = datetime.fromisoformat(created_at)
        return round((datetime.now() - created).total_seconds(), 1)
    except (TypeError, ValueError):
        return None


def _engine_ready() -> bool:
    return (config.ENGINE_ROOT / "Run_PY").is_dir() and config.t1_runner_path().exists()


def _hybrid_health() -> dict:
    try:
        from services.hybrid_shadow_service import hybrid_health

        return hybrid_health()
    except Exception:
        return {
            "mode": "unknown",
            "api_key_status": "UNKNOWN",
            "api_key_configured": False,
            "production_excel_invokes_claude": False,
            "shadow_may_invoke_claude": False,
            "authoritative_enabled": False,
            "production_authority": "none",
        }


@bp.get("/health")
def health():
    from datetime import datetime, timezone

    engine_root = str(config.ENGINE_ROOT.resolve())
    return jsonify({
        "status": "ok",
        "service": "steel-beam-estimation",
        "phase": "W.19",
        "app_release": current_app.config.get("APP_RELEASE"),
        "engine_label": current_app.config.get("ENGINE_LABEL"),
        "engine_display": current_app.config.get("ENGINE_DISPLAY"),
        "engine_ready": _engine_ready(),
        "engine_root": engine_root,
        "t1_included": config.t1_is_configured(),
        "t1_runner": str(config.t1_runner_path()),
        "production_stages": [s["id"] for s in config.PRODUCTION_STAGES],
        "busy": active_run_id() is not None,
        "active_run_id": active_run_id(),
        "web_runs_root": str(config.WEB_RUNS_ROOT.resolve()),
        "upload_folder": str(config.UPLOAD_ROOT.resolve()),
        "run_context": {
            "STEEL_ENGINE_ROOT": engine_root,
            "STEEL_RUN_ROOT": "<web_runs>/<run_id>",
            "STEEL_OUTPUT_ROOT": "<web_runs>/<run_id>/data/output",
        },
        "hybrid": _hybrid_health(),
        "result_delivery": {
            "durable_registry": True,
            "download_reconstructs_from_disk": True,
            "retention": "completed workbooks retained until operator cleanup",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@bp.get("/")
def home():
    return render_template(
        "index.html",
        engine_display=current_app.config.get("ENGINE_DISPLAY"),
        app_release=current_app.config.get("APP_RELEASE"),
    )


@bp.post("/api/estimate")
def api_estimate():
    try:
        run_id = start_estimation(
            general_notes=request.files.get("general_notes"),
            framing=request.files.get("framing"),
            reinforcement=request.files.get("reinforcement"),
        )
        return jsonify({"ok": True, "run_id": run_id})
    except EstimationBusyError as exc:
        return jsonify({"ok": False, "error": str(exc), "code": "BUSY"}), 409
    except EstimationError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        current_app.logger.exception("api_estimate failed")
        return jsonify({
            "ok": False,
            "error": "Unable to start estimation. Please check the uploaded files and try again.",
        }), 500


@bp.get("/api/status/<run_id>")
def api_status(run_id: str):
    if not is_valid_run_id(run_id):
        return jsonify({
            "ok": False,
            "error": "Unknown run id.",
            "classification": CLASS_INVALID_RUN,
        }), 404
    job = get_job(run_id)
    if job is None:
        return jsonify({
            "ok": False,
            "error": "Unknown run id.",
            "classification": CLASS_INVALID_RUN,
        }), 404
    progress = _load_hybrid_progress(run_id)
    message = job.message
    if job.status == "running" and isinstance(progress, dict) and progress.get("label"):
        message = str(progress.get("label"))
    elapsed_s = _elapsed_s(job.created_at)
    return jsonify({
        "ok": True,
        "run_id": job.run_id,
        "status": job.status,
        "message": message,
        "elapsed_s": elapsed_s,
        "progress": progress,
        "workbook_name": job.workbook_name,
        "duration_s": job.duration_s,
        "error": job.error,
        "filenames": job.filenames,
        "created_at": job.created_at,
        "summary": job.summary,
        "warnings": job.warnings,
        "stages_run": job.stages_run,
        "t1_executed": job.t1_executed,
        "engine_root": job.engine_root,
        "hybrid": job.hybrid_summary or None,
        "result_lifecycle": job.result_lifecycle,
        "excel_generated": bool(job.excel_generated),
        "excel_exists": bool(job.excel_exists),
        "result_registered": bool(job.result_registered),
        "download_ready": bool(job.download_ready),
    })


@bp.get("/api/download/<run_id>")
def api_download(run_id: str):
    classification, path, error = resolve_download(run_id)
    if classification == CLASS_INVALID_RUN or classification == CLASS_TRAVERSAL:
        return jsonify({
            "ok": False,
            "error": error,
            "classification": classification,
            "download_ready": False,
        }), 404
    if classification == CLASS_UNAVAILABLE:
        record_download_attempt(
            run_id, http_status=404, classification=classification, ok=False
        )
        return jsonify({
            "ok": False,
            "error": error,
            "classification": classification,
            "download_ready": False,
        }), 404
    if classification == CLASS_NOT_READY or path is None:
        record_download_attempt(
            run_id, http_status=400, classification=classification, ok=False
        )
        return jsonify({
            "ok": False,
            "error": error,
            "classification": classification,
            "download_ready": False,
        }), 400
    if classification != CLASS_OK:
        record_download_attempt(
            run_id, http_status=404, classification=classification, ok=False
        )
        return jsonify({
            "ok": False,
            "error": error or "Workbook file is missing.",
            "classification": classification,
            "download_ready": False,
        }), 404
    job = get_job(run_id)
    download_name = (
        (job.workbook_name if job else None) or workbook_filename(run_id)
    )
    record_download_attempt(
        run_id, http_status=200, classification=CLASS_OK, ok=True
    )
    return send_file(
        path,
        as_attachment=True,
        download_name=download_name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        max_age=0,
        conditional=False,
    )
