"""
Flask routes — production web application.
MODEL_VERSION: 8.9.5
"""
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
    EstimationError,
    get_job,
    start_estimation,
)

bp = Blueprint("ui", __name__)


@bp.get("/health")
def health():
    from datetime import datetime, timezone

    engine_root = str(config.V8_ROOT.resolve())
    web_runs = str(config.WEB_RUNS_ROOT.resolve())
    return jsonify({
        "status": "ok",
        "service": "steel-beam-estimation",
        "phase": "Production Ready",
        "production_status": "stable_baseline",
        "model_version": current_app.config.get("MODEL_VERSION"),
        "engine_ready": (config.V8_ROOT / "Run_PY").is_dir(),
        "engine_root": engine_root,
        "web_runs_root": web_runs,
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
    return render_template("index.html", model_version=current_app.config.get("MODEL_VERSION"))


@bp.post("/api/estimate")
def api_estimate():
    try:
        run_id = start_estimation(
            general_notes=request.files.get("general_notes"),
            framing=request.files.get("framing"),
            reinforcement=request.files.get("reinforcement"),
        )
        return jsonify({"ok": True, "run_id": run_id})
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
    return send_file(
        path,
        as_attachment=True,
        download_name=job.workbook_name or path.name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
