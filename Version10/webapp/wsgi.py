"""
WSGI entry for production process managers.

Live Lightsail Gunicorn target (cwd = Version10/webapp):

    gunicorn --config deployment/gunicorn.w3.conf.py wsgi:app

Confirmed bind: 127.0.0.1:8001 (see gunicorn.w3.conf.py).
workers MUST remain 1 (in-process job store + single-flight guard).
APP_RELEASE: W.19.1 (Version10 Hybrid).
"""
from __future__ import annotations

from app import app

__all__ = ["app"]
