"""
Phase D.3 — Flask application factory.

Creates the app, loads configuration, initialises logging, registers routes,
and ensures runtime folders exist. No estimation business logic here.
"""
from __future__ import annotations

from flask import Flask

from config.paths import STATIC_DIR, TEMPLATES_DIR, ensure_runtime_dirs
from config.settings import MODEL_VERSION, apply_flask_config
from webapp.logging_config import configure_logging
from webapp.routes import bp


def create_app() -> Flask:
    ensure_runtime_dirs()
    logger = configure_logging()

    app = Flask(
        __name__,
        template_folder=str(TEMPLATES_DIR),
        static_folder=str(STATIC_DIR),
    )
    apply_flask_config(app)
    app.register_blueprint(bp)

    logger.info(
        "Application start — model_version=%s engine_root=%s engine_ready=%s",
        MODEL_VERSION,
        app.config.get("ENGINE_ROOT"),
        app.config.get("ENGINE_READY"),
    )
    return app


app = create_app()
