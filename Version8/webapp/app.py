"""
Phase UI.1 — Steel Beam Estimation Web Application
MODEL_VERSION: 8.9.2

Presentation layer only. Invokes existing Version8 production runners.
Does not modify engineering logic.

Run (from Version8/webapp):
    pip install -r requirements.txt
    python app.py

Then open http://127.0.0.1:5000
"""
from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask

import config
from routes import bp

MODEL_VERSION = "8.9.2"


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
    app.config["MODEL_VERSION"] = MODEL_VERSION

    config.UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    config.LOG_ROOT.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    app.register_blueprint(bp)
    return app


app = create_app()


if __name__ == "__main__":
    # Development server. Production: gunicorn "app:app"
    app.run(host="0.0.0.0", port=5000, debug=False)
