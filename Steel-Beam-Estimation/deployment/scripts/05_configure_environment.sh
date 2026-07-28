#!/usr/bin/env bash
# 05_configure_environment.sh — Create/update .env for Mode B engine wiring (Phase D.4.2)
# Never overwrites an existing SECRET_KEY. Upserts STEEL_ENGINE_ROOT when discoverable.

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

require_model_root

ENV_FILE="${MODEL_ROOT}/.env"
EXAMPLE="${MODEL_ROOT}/.env.example"

discover_engine_root() {
  if [[ -n "${STEEL_ENGINE_ROOT:-}" && -d "${STEEL_ENGINE_ROOT}/Run_PY" ]]; then
    echo "${STEEL_ENGINE_ROOT}"
    return 0
  fi
  if [[ -d "${REPOSITORY_ROOT}/Version8/Run_PY" ]]; then
    echo "${REPOSITORY_ROOT}/Version8"
    return 0
  fi
  echo ""
}

upsert_env_key() {
  local key="$1"
  local value="$2"
  local tmp cur
  touch "${ENV_FILE}"
  if grep -qE "^[[:space:]]*${key}=" "${ENV_FILE}"; then
    cur="$(grep -E "^[[:space:]]*${key}=" "${ENV_FILE}" | head -n1 | cut -d= -f2- | tr -d "\"'" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
    if [[ -n "${cur}" && "${cur}" != "change-me-to-a-long-random-string" ]]; then
      # Keep operator-provided non-empty value
      return 0
    fi
    tmp="$(mktemp)"
    grep -vE "^[[:space:]]*${key}=" "${ENV_FILE}" > "${tmp}" || true
    printf "%s=%s\n" "${key}" "${value}" >> "${tmp}"
    mv "${tmp}" "${ENV_FILE}"
  else
    printf "\n%s=%s\n" "${key}" "${value}" >> "${ENV_FILE}"
  fi
}

if [[ ! -f "${ENV_FILE}" ]]; then
  [[ -f "${EXAMPLE}" ]] || die "Missing ${EXAMPLE}"
  info "Creating ${ENV_FILE} from .env.example"
  cp "${EXAMPLE}" "${ENV_FILE}"
  chmod 600 "${ENV_FILE}" || true
else
  info ".env already exists at ${ENV_FILE} — leaving secrets unchanged"
fi

ENGINE="$(discover_engine_root)"
if [[ -n "${ENGINE}" ]]; then
  upsert_env_key "STEEL_ENGINE_ROOT" "${ENGINE}"
  info "STEEL_ENGINE_ROOT → ${ENGINE}"
else
  warn "Could not auto-discover Version8 engine — set STEEL_ENGINE_ROOT in ${ENV_FILE}"
fi

mkdir -p \
  "${MODEL_ROOT}/uploads" \
  "${MODEL_ROOT}/temp" \
  "${MODEL_ROOT}/outputs" \
  "${MODEL_ROOT}/logs" \
  || true
if [[ -n "${ENGINE}" ]]; then
  mkdir -p "${ENGINE}/data/web_runs" "${ENGINE}/data/output" || true
fi

warn "Edit ${ENV_FILE} before production start:"
warn "  - set SECRET_KEY (required when FLASK_ENV=production)"
warn "  - set FLASK_ENV=production"
warn "  - confirm STEEL_ENGINE_ROOT points at Version8 (absolute path)"

info "Environment configuration complete"
