"""
Steel Beam Estimation Web Application — Version10 adapter (Phase W.2).

Presentation layer only. Invokes Version10 production runners via RunContext.
Does not modify engineering logic.

Run (from Version10/webapp):
    pip install -r ../requirements.txt
    pip install -r requirements.txt
    python app.py

Then open http://127.0.0.1:5000
"""
from __future__ import annotations

import logging

from flask import Flask

import config
from routes import bp

APP_RELEASE = config.APP_RELEASE
ENGINE_LABEL = config.ENGINE_LABEL


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
    app.config["APP_RELEASE"] = APP_RELEASE
    app.config["ENGINE_LABEL"] = ENGINE_LABEL
    app.config["ENGINE_DISPLAY"] = config.ENGINE_DISPLAY

    config.UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    config.LOG_ROOT.mkdir(parents=True, exist_ok=True)
    config.WEB_RUNS_ROOT.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    app.register_blueprint(bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
