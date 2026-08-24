# PREPARED FOR FUTURE DEPLOYMENT — NOT YET DEPLOYED.
# Phase W.2.1 local Gunicorn template for Version10/webapp.
#
# Launch (from Version10/webapp):
#   gunicorn --config deployment/gunicorn.w21.conf.py "wsgi:app"
#
# workers MUST be 1. Do not raise this without redesigning job state.

bind = "127.0.0.1:8000"
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
