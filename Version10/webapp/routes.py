"""Flask routes — Version10 web adapter (Phase W.2)."""
from __future__ import annotations

from pathlib import Path

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

bp = Blueprint("ui", __name__)


def _engine_ready() -> bool:
    return (config.ENGINE_ROOT / "Run_PY").is_dir() and config.t1_runner_path().exists()


@bp.get("/health")
def health():
    from datetime import datetime, timezone

    engine_root = str(config.ENGINE_ROOT.resolve())
    return jsonify({
        "status": "ok",
        "service": "steel-beam-estimation",
        "phase": "W.3",
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
    job = get_job(run_id)
    if job is None:
        return jsonify({"ok": False, "error": "Unknown run id."}), 404
    return jsonify({
        "ok": True,
        "run_id": job.run_id,
        "status": job.status,
        "message": job.message,
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
    })


@bp.get("/api/download/<run_id>")
def api_download(run_id: str):
    job = get_job(run_id)
    if job is None:
        return jsonify({"ok": False, "error": "Unknown run id."}), 404
    if job.status != "success" or not job.workbook_path:
        return jsonify({"ok": False, "error": "Workbook is not ready for download."}), 400
    path = Path(job.workbook_path)
    if not path.exists():
        return jsonify({"ok": False, "error": "Workbook file is missing."}), 404
    try:
        path.resolve().relative_to(config.OUTPUT_ROOT.resolve())
    except ValueError:
        return jsonify({"ok": False, "error": "Workbook file is missing."}), 404
    return send_file(
        path,
        as_attachment=True,
        download_name=job.workbook_name or path.name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
