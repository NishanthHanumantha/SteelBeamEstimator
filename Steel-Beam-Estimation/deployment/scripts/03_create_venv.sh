#!/usr/bin/env bash
# 03_create_venv.sh — Create Python virtualenv under current_model/ (Phase D.4)
# Idempotent: recreates only if missing; leave existing venv intact.

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

# Resolve MODEL_ROOT when flat package layout is used
if [[ ! -d "${MODEL_ROOT}" && -d "${APPLICATION_DIRECTORY}/current_model" ]]; then
  MODEL_ROOT="${APPLICATION_DIRECTORY}/current_model"
  VENV_DIR="${MODEL_ROOT}/${VIRTUAL_ENVIRONMENT_NAME}"
  VENV_BIN="${VENV_DIR}/bin"
fi

[[ -d "${MODEL_ROOT}" ]] || die "Model root not found: ${MODEL_ROOT}"

PYTHON_BIN="python${PYTHON_VERSION}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi
require_cmd "${PYTHON_BIN}"

if [[ -x "${VENV_BIN}/python" ]]; then
  info "Virtualenv already exists at ${VENV_DIR} — skipping create"
  "${VENV_BIN}/python" -V
  exit 0
fi

info "Creating virtualenv ${VENV_DIR} with ${PYTHON_BIN}"
"${PYTHON_BIN}" -m venv "${VENV_DIR}"
"${VENV_BIN}/python" -m pip install --upgrade pip setuptools wheel

info "Virtualenv ready: ${VENV_DIR}"
