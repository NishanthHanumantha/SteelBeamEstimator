#!/usr/bin/env bash
# 04_install_requirements.sh — Install app (+ optional engine) requirements (Phase D.4)
# Idempotent: pip install is safe to re-run.

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

if [[ ! -d "${MODEL_ROOT}" && -d "${APPLICATION_DIRECTORY}/current_model" ]]; then
  MODEL_ROOT="${APPLICATION_DIRECTORY}/current_model"
  VENV_DIR="${MODEL_ROOT}/${VIRTUAL_ENVIRONMENT_NAME}"
  VENV_BIN="${VENV_DIR}/bin"
fi

[[ -x "${VENV_BIN}/pip" ]] || die "Virtualenv missing. Run 03_create_venv.sh first."
REQ_FILE="${MODEL_ROOT}/requirements.txt"
[[ -f "${REQ_FILE}" ]] || die "Missing ${REQ_FILE}"

info "Installing application requirements from ${REQ_FILE}"
"${VENV_BIN}/pip" install -r "${REQ_FILE}"

# If STEEL_ENGINE_ROOT is set and has requirements, install those too
if [[ -n "${STEEL_ENGINE_ROOT:-}" && -f "${STEEL_ENGINE_ROOT}/requirements.txt" ]]; then
  info "Installing engine requirements from ${STEEL_ENGINE_ROOT}/requirements.txt"
  "${VENV_BIN}/pip" install -r "${STEEL_ENGINE_ROOT}/requirements.txt"
elif [[ -f "${MODEL_ROOT}/Run_PY" || -d "${MODEL_ROOT}/Run_PY" ]]; then
  if [[ -f "${MODEL_ROOT}/requirements-engine.txt" ]]; then
    info "Installing packaged engine requirements"
    "${VENV_BIN}/pip" install -r "${MODEL_ROOT}/requirements-engine.txt"
  else
    info "Engine appears packaged under current_model; no extra requirements file found"
  fi
else
  info "No STEEL_ENGINE_ROOT set — app framework deps only"
fi

info "Requirements install complete"
