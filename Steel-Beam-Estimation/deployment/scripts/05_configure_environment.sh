#!/usr/bin/env bash
# 05_configure_environment.sh — Create .env from template if missing (Phase D.4)
# Idempotent: never overwrites an existing .env (fail-safe for secrets).

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

if [[ ! -d "${MODEL_ROOT}" && -d "${APPLICATION_DIRECTORY}/current_model" ]]; then
  MODEL_ROOT="${APPLICATION_DIRECTORY}/current_model"
fi

[[ -d "${MODEL_ROOT}" ]] || die "Model root not found: ${MODEL_ROOT}"

ENV_FILE="${MODEL_ROOT}/.env"
EXAMPLE="${MODEL_ROOT}/.env.example"

if [[ -f "${ENV_FILE}" ]]; then
  info ".env already exists at ${ENV_FILE} — leaving unchanged"
  exit 0
fi

[[ -f "${EXAMPLE}" ]] || die "Missing ${EXAMPLE}"

info "Creating ${ENV_FILE} from .env.example"
cp "${EXAMPLE}" "${ENV_FILE}"
chmod 600 "${ENV_FILE}" || true

warn "Edit ${ENV_FILE} before production start:"
warn "  - set SECRET_KEY (required when FLASK_ENV=production)"
warn "  - set FLASK_ENV=production"
warn "  - set STEEL_ENGINE_ROOT if engine is external"
warn "  - set STEEL_BEAM_HOST/PORT only if needed for local run.py"

info "Environment template installed (secrets must be filled manually)"
