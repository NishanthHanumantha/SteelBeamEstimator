#!/usr/bin/env bash
# 06_validate_application.sh — Packaging / health contract checks (Phase D.4.1)

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

require_project_root
require_model_root

VALIDATE_PY="${PROJECT_ROOT}/deployment/scripts/validate_packaging.py"
if [[ -f "${VALIDATE_PY}" ]]; then
  info "Running packaging validator"
  PYTHON_BIN="${VENV_BIN}/python"
  if [[ ! -x "${PYTHON_BIN}" ]]; then
    PYTHON_BIN="python3"
  fi
  "${PYTHON_BIN}" "${VALIDATE_PY}"
else
  warn "validate_packaging.py not found — performing minimal checks"
  [[ -f "${MODEL_ROOT}/wsgi.py" ]] || die "Missing ${MODEL_ROOT}/wsgi.py"
  [[ -f "${MODEL_ROOT}/run.py" ]] || die "Missing ${MODEL_ROOT}/run.py"
  [[ -f "${MODEL_ROOT}/requirements.txt" ]] || die "Missing requirements.txt"
fi

info "Application validation complete"
info "  PROJECT_ROOT=${PROJECT_ROOT}"
info "  MODEL_ROOT=${MODEL_ROOT}"
