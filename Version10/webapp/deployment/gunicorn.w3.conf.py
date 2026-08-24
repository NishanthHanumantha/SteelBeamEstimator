# Phase W.3 — Version10 Gunicorn (alongside 8.9.5 on :8000).
# Bind is loopback-only. workers MUST remain 1.

bind = "127.0.0.1:8001"
workers = 1
threads = 4
timeout = 3600
graceful_timeout = 60
keepalive = 5
worker_class = "sync"
proc_name = "steel-beam-estimator-v10"
accesslog = "-"
errorlog = "-"
loglevel = "info"
capture_output = True
preload_app = False
