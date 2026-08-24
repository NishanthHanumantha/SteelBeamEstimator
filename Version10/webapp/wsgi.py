"""
WSGI entry for production process managers (Phase W.2.1).

PREPARED FOR FUTURE DEPLOYMENT — NOT YET DEPLOYED.

Confirmed target (cwd = Version10/webapp):

    gunicorn --workers 1 --timeout 3600 --bind 127.0.0.1:8000 "wsgi:app"

workers MUST remain 1 (in-process job store + single-flight guard).
"""
from __future__ import annotations

from app import app

__all__ = ["app"]
