"""
WSGI entry for production process managers (Phase D.3).

Example (later phase):
    gunicorn -b 0.0.0.0:5000 --timeout 3600 "wsgi:app"

No engineering logic here.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from webapp.app import app  # noqa: E402

__all__ = ["app"]
