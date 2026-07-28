#!/usr/bin/env bash
# 03_create_venv.sh — Create or reuse venv under MODEL_ROOT (Phase D.4.1)
# Never assumes a fixed layout; uses paths from _common.sh only.

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

require_project_root
require_model_root

PYTHON_BIN="python${PYTHON_VERSION}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi
require_cmd "${PYTHON_BIN}"

info "MODEL_ROOT=${MODEL_ROOT}"
info "VENV_DIR=${VENV_DIR}"

if [[ -x "${VENV_BIN}/python" ]]; then
  info "Virtualenv already exists — reusing"
  "${VENV_BIN}/python" -V
  exit 0
fi

info "Creating virtualenv with ${PYTHON_BIN}"
"${PYTHON_BIN}" -m venv "${VENV_DIR}"
"${VENV_BIN}/python" -m pip install --upgrade pip setuptools wheel

info "Virtualenv ready: ${VENV_DIR}"
