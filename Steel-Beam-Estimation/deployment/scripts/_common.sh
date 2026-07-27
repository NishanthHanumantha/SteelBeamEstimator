#!/usr/bin/env bash
# Shared helpers for Steel Beam Estimation deployment scripts (Phase D.4).
# Source this file from each numbered script:  source "$(dirname "$0")/_common.sh"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PACKAGE_DIR="$(cd "${DEPLOYMENT_DIR}/.." && pwd)"
CONFIG_FILE="${DEPLOYMENT_DIR}/config.yaml"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

info() {
  echo "[INFO] $*"
}

warn() {
  echo "[WARN] $*" >&2
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

# Minimal YAML key reader for flat "key: value" lines (no nested structures).
yaml_get() {
  local key="$1"
  local default="${2:-}"
  local line
  if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "${default}"
    return 0
  fi
  line="$(grep -E "^${key}:" "${CONFIG_FILE}" | head -n1 || true)"
  if [[ -z "${line}" ]]; then
    echo "${default}"
    return 0
  fi
  # Strip key, colon, quotes, inline comments
  echo "${line}" | sed -E "s/^${key}:[[:space:]]*//; s/[\"']//g; s/[[:space:]]+#.*$//; s/[[:space:]]+$//"
}

load_config() {
  SERVER_IP="$(yaml_get server_ip "0.0.0.0")"
  SSH_USER="$(yaml_get ssh_user "ubuntu")"
  APPLICATION_DIRECTORY="$(yaml_get application_directory "/opt/steel-beam-estimation")"
  GITHUB_REPOSITORY="$(yaml_get github_repository "")"
  BRANCH="$(yaml_get branch "main")"
  PYTHON_VERSION="$(yaml_get python_version "3.12")"
  VIRTUAL_ENVIRONMENT_NAME="$(yaml_get virtual_environment_name ".venv")"
  GUNICORN_SERVICE_NAME="$(yaml_get gunicorn_service_name "steel-beam-estimator")"
  NGINX_SITE_NAME="$(yaml_get nginx_site_name "steel-beam-estimator")"
  GUNICORN_BIND="$(yaml_get gunicorn_bind "127.0.0.1:8000")"
  GUNICORN_WORKERS="$(yaml_get gunicorn_workers "2")"
  GUNICORN_TIMEOUT="$(yaml_get gunicorn_timeout "3600")"
  APP_SUBDIRECTORY="$(yaml_get app_subdirectory "Steel-Beam-Estimation")"
  MODEL_SUBDIRECTORY="$(yaml_get model_subdirectory "current_model")"

  REPO_ROOT="${APPLICATION_DIRECTORY}"
  APP_ROOT="${APPLICATION_DIRECTORY}/${APP_SUBDIRECTORY}"
  MODEL_ROOT="${APP_ROOT}/${MODEL_SUBDIRECTORY}"
  VENV_DIR="${MODEL_ROOT}/${VIRTUAL_ENVIRONMENT_NAME}"
  VENV_BIN="${VENV_DIR}/bin"
  GUNICORN_CONF="${APP_ROOT}/deployment/gunicorn/gunicorn.conf.py"
  NGINX_CONF_SRC="${APP_ROOT}/deployment/nginx/${NGINX_SITE_NAME}.conf"
  SYSTEMD_UNIT_SRC="${APP_ROOT}/deployment/systemd/${GUNICORN_SERVICE_NAME}.service"
}

load_config

require_root_or_sudo() {
  if [[ "${EUID}" -ne 0 ]]; then
    if command -v sudo >/dev/null 2>&1; then
      SUDO="sudo"
    else
      die "This step requires root privileges (sudo not available)."
    fi
  else
    SUDO=""
  fi
}
