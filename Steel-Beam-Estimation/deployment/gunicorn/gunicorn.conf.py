"""
Gunicorn configuration — Steel Beam Reinforcement Estimation (Phase D.4).

Used with: current_model/wsgi.py  →  "wsgi:app"

Paths and bind address are intended to be overridden via environment or the
systemd unit. Do not hardcode model version directory names.
"""
from __future__ import annotations

import os

# ── Bind / process ───────────────────────────────────────────────────────────
_bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")
bind = _bind

_workers = os.environ.get("GUNICORN_WORKERS")
if _workers:
    workers = int(_workers)
else:
    # In-memory job store (_JOBS) is per-process. Multiple sync workers cause
    # /api/status/<run_id> 404 when the poll hits a different worker than /api/estimate.
    workers = 1

threads = int(os.environ.get("GUNICORN_THREADS", "4"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "3600"))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", "60"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5"))

# ── Process naming ───────────────────────────────────────────────────────────
proc_name = os.environ.get("GUNICORN_PROC_NAME", "steel-beam-estimator")

# ── Logging (stdout/stderr → journald when run under systemd) ────────────────
accesslog = os.environ.get("GUNICORN_ACCESS_LOG", "-")
errorlog = os.environ.get("GUNICORN_ERROR_LOG", "-")
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
capture_output = True

# ── Worker class ─────────────────────────────────────────────────────────────
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "sync")

# ── Security / limits ────────────────────────────────────────────────────────
limit_request_line = 8190
limit_request_fields = 100
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "500"))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", "50"))

# Prefork: load app once per worker
preload_app = False
