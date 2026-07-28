#!/usr/bin/env bash
# 04_install_requirements.sh — Install app (+ engine) requirements (Phase D.4.2)

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

require_model_root
[[ -x "${VENV_BIN}/pip" ]] || die "Virtualenv missing at ${VENV_DIR}. Run 03_create_venv.sh first."

REQ_FILE="${MODEL_ROOT}/requirements.txt"
[[ -f "${REQ_FILE}" ]] || die "Missing ${REQ_FILE}"

info "Installing application requirements from ${REQ_FILE}"
"${VENV_BIN}/pip" install -r "${REQ_FILE}"

# Resolve engine root: shell env → .env → monorepo sibling Version8 → packaged Run_PY
resolve_engine_for_install() {
  local val=""
  if [[ -n "${STEEL_ENGINE_ROOT:-}" ]]; then
    echo "${STEEL_ENGINE_ROOT}"
    return 0
  fi
  if [[ -f "${MODEL_ROOT}/.env" ]]; then
    val="$(grep -E '^[[:space:]]*STEEL_ENGINE_ROOT=' "${MODEL_ROOT}/.env" | head -n1 || true)"
    if [[ -n "${val}" ]]; then
      val="${val#*=}"
      val="${val%\"}"
      val="${val#\"}"
      val="${val%\'}"
      val="${val#\'}"
      val="$(echo "${val}" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
      if [[ -n "${val}" ]]; then
        echo "${val}"
        return 0
      fi
    fi
  fi
  if [[ -d "${REPOSITORY_ROOT}/Version8/Run_PY" ]]; then
    echo "${REPOSITORY_ROOT}/Version8"
    return 0
  fi
  if [[ -d "${MODEL_ROOT}/Run_PY" ]]; then
    echo "${MODEL_ROOT}"
    return 0
  fi
  echo ""
}

ENGINE_ROOT_RESOLVED="$(resolve_engine_for_install)"

if [[ -n "${ENGINE_ROOT_RESOLVED}" && -f "${ENGINE_ROOT_RESOLVED}/requirements.txt" ]]; then
  info "Installing engine requirements from ${ENGINE_ROOT_RESOLVED}/requirements.txt"
  "${VENV_BIN}/pip" install -r "${ENGINE_ROOT_RESOLVED}/requirements.txt"
elif [[ -d "${MODEL_ROOT}/Run_PY" ]]; then
  if [[ -f "${MODEL_ROOT}/requirements-engine.txt" ]]; then
    info "Installing packaged engine requirements"
    "${VENV_BIN}/pip" install -r "${MODEL_ROOT}/requirements-engine.txt"
  else
    info "Engine appears packaged under current_model; no extra requirements file found"
  fi
else
  warn "No STEEL_ENGINE_ROOT / Version8 requirements found — app framework deps only"
  warn "VROOT1 will report 0 text entities until ezdxf is installed into ${VENV_DIR}"
fi

info "Requirements install complete"
# Smoke-check ezdxf when engine was resolved
if [[ -n "${ENGINE_ROOT_RESOLVED}" ]]; then
  if "${VENV_BIN}/python" -c "import ezdxf" 2>/dev/null; then
    info "ezdxf import OK in ${VENV_DIR}"
  else
    warn "ezdxf still not importable after install — check ${ENGINE_ROOT_RESOLVED}/requirements.txt"
  fi
fi
