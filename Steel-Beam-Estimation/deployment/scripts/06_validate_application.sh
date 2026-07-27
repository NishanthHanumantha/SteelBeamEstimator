#!/usr/bin/env bash
# 06_validate_application.sh — Smoke-check packaging + /health (Phase D.4)
# Idempotent: read-only validation.

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

if [[ ! -d "${MODEL_ROOT}" && -d "${APPLICATION_DIRECTORY}/current_model" ]]; then
  MODEL_ROOT="${APPLICATION_DIRECTORY}/current_model"
  APP_ROOT="${APPLICATION_DIRECTORY}"
fi

[[ -d "${MODEL_ROOT}" ]] || die "Model root not found: ${MODEL_ROOT}"

VALIDATE_PY="${APP_ROOT}/deployment/scripts/validate_packaging.py"
if [[ -f "${VALIDATE_PY}" ]]; then
  info "Running packaging validator"
  PYTHON_BIN="${VENV_BIN}/python"
  if [[ ! -x "${PYTHON_BIN}" ]]; then
    PYTHON_BIN="python3"
  fi
  # validate_packaging discovers package relative to script location
  "${PYTHON_BIN}" "${VALIDATE_PY}"
else
  warn "validate_packaging.py not found — performing minimal checks"
  [[ -f "${MODEL_ROOT}/wsgi.py" ]] || die "Missing wsgi.py"
  [[ -f "${MODEL_ROOT}/run.py" ]] || die "Missing run.py"
  [[ -f "${MODEL_ROOT}/requirements.txt" ]] || die "Missing requirements.txt"
fi

info "Application validation complete"
