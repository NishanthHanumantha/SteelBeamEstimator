"""
Phase D.2 — HTTP routes (presentation only).
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

from webapp.services import EstimationError, get_job, start_estimation

bp = Blueprint("ui", __name__)


@bp.get("/health")
def health():
    from datetime import datetime, timezone

    return jsonify({
        "status": "ok",
        "service": "steel-beam-estimation",
        "phase": "D.3",
        "model_version": current_app.config.get("MODEL_VERSION"),
        "engine_ready": bool(current_app.config.get("ENGINE_READY")),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@bp.get("/")
def home():
    return render_template(
        "index.html",
        model_version=current_app.config.get("MODEL_VERSION"),
    )


@bp.post("/api/estimate")
def api_estimate():
    current_app.logger.info("Upload received — estimate request")
    try:
        run_id = start_estimation(
            general_notes=request.files.get("general_notes"),
            framing=request.files.get("framing"),
            reinforcement=request.files.get("reinforcement"),
        )
        return jsonify({"ok": True, "run_id": run_id})
    except EstimationError as exc:
        current_app.logger.warning("Estimate rejected: %s", exc)
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
