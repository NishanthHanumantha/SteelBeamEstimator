"""
Flask-facing config re-exports (Phase D.5.2).

Canonical settings live in config.settings — keep this module thin.
"""
from __future__ import annotations

from config import settings as _settings

SECRET_KEY = _settings.SECRET_KEY
MAX_CONTENT_LENGTH = _settings.MAX_CONTENT_LENGTH
MAX_UPLOAD_MB = _settings.MAX_UPLOAD_MB
ALLOWED_EXTENSIONS = _settings.ALLOWED_EXTENSIONS
MODEL_VERSION = _settings.MODEL_VERSION
MODEL_INFO = _settings.MODEL_INFO

UPLOAD_FOLDER = _settings.UPLOAD_FOLDER
OUTPUT_FOLDER = _settings.OUTPUT_FOLDER
TEMP_FOLDER = _settings.TEMP_FOLDER
LOG_FOLDER = _settings.LOG_FOLDER
INPUTS_FOLDER = _settings.INPUTS_FOLDER

ENGINE_ROOT = _settings.ENGINE_ROOT
V7_ROOT = _settings.V7_ROOT
WEB_RUNS_ROOT = _settings.WEB_RUNS_ROOT
PRODUCTION_EXCEL = _settings.PRODUCTION_EXCEL
PRODUCTION_STAGES = _settings.PRODUCTION_STAGES
R2A_GN_POINTER = _settings.R2A_GN_POINTER
R21C_FACTS_REL = _settings.R21C_FACTS_REL
R21D_FACTS_REL = _settings.R21D_FACTS_REL
ARTEFACT_SEED_ROOT = _settings.ARTEFACT_SEED_ROOT
HOST = _settings.HOST
PORT = _settings.PORT
