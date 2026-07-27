"""
Local execution entry point — Phase D.2.

    python run.py

Starts Flask at http://127.0.0.1:5000 by default.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.paths import ensure_runtime_dirs  # noqa: E402
from config.settings import HOST, PORT  # noqa: E402


def main() -> None:
    ensure_runtime_dirs()
    from webapp.app import app

    # Development server. Production: gunicorn (later deployment phase).
    app.run(host=HOST, port=PORT, debug=False)


if __name__ == "__main__":
    main()
