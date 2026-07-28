#!/usr/bin/env bash
# Shared helpers for Steel Beam Estimation deployment scripts (Phase D.4.1).
#
# THIS IS THE ONLY PLACE WHERE DEPLOYMENT PATHS ARE CALCULATED.
# Every numbered script must:  source "$(dirname "$0")/_common.sh"
# and consume the exported variables — never recompute MODEL_ROOT / PROJECT_ROOT.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# PACKAGE_DIR = Steel-Beam-Estimation/ (project package containing deployment/)
PACKAGE_DIR="$(cd "${DEPLOYMENT_DIR}/.." && pwd)"
CONFIG_FILE="${DEPLOYMENT_DIR}/config.yaml"

# ── Logging ──────────────────────────────────────────────────────────────────

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

# ── YAML (flat key: value) ───────────────────────────────────────────────────

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
  echo "${line}" | sed -E "s/^${key}:[[:space:]]*//; s/[\"']//g; s/[[:space:]]+#.*$//; s/[[:space:]]+$//"
}

# ── Config load (no paths yet) ───────────────────────────────────────────────

load_config_keys() {
  DEPLOYMENT_PACKAGE_VERSION="$(yaml_get deployment_package_version "D.4.1")"
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

  # Preferred D.4.1 keys
  REPOSITORY_DIRECTORY="$(yaml_get repository_directory "")"
  PROJECT_DIRECTORY="$(yaml_get project_directory "")"
  MODEL_DIRECTORY="$(yaml_get model_directory "")"

  # Legacy D.4 keys (backwards compatible)
  local legacy_app legacy_model
  legacy_app="$(yaml_get app_subdirectory "")"
  legacy_model="$(yaml_get model_subdirectory "")"

  if [[ -z "${PROJECT_DIRECTORY}" ]]; then
    PROJECT_DIRECTORY="${legacy_app:-Steel-Beam-Estimation}"
  fi
  if [[ -z "${MODEL_DIRECTORY}" ]]; then
    MODEL_DIRECTORY="${legacy_model:-current_model}"
  fi
  # repository_directory may be empty (Mode A: project directly under application_directory)
}

# ── Path helpers ─────────────────────────────────────────────────────────────

_path_join() {
  # Join non-empty segments with /
  local result="" seg
  for seg in "$@"; do
    [[ -n "${seg}" ]] || continue
    if [[ -z "${result}" ]]; then
      result="${seg}"
    else
      result="${result%/}/${seg#/}"
    fi
  done
  echo "${result}"
}

_is_project_root() {
  local candidate="$1"
  [[ -d "${candidate}/${MODEL_DIRECTORY}" ]] \
    && [[ -d "${candidate}/deployment" ]] \
    && [[ -f "${candidate}/deployment/config.yaml" || -f "${candidate}/deployment/scripts/_common.sh" ]]
}

_is_model_root() {
  local candidate="$1"
  [[ -d "${candidate}" ]] \
    && [[ -f "${candidate}/wsgi.py" || -f "${candidate}/run.py" || -d "${candidate}/webapp" ]]
}

_discover_current_model_dirs() {
  local root="$1"
  local -a found=()
  local d
  # Limit depth to avoid scanning huge trees
  while IFS= read -r d; do
    [[ -n "${d}" ]] || continue
    if _is_model_root "${d}"; then
      found+=("${d}")
    fi
  done < <(find "${root}" -maxdepth 6 -type d -name "${MODEL_DIRECTORY}" 2>/dev/null || true)

  if [[ ${#found[@]} -eq 0 ]]; then
    return 1
  fi
  if [[ ${#found[@]} -gt 1 ]]; then
    echo ""
    echo "ERROR: Multiple '${MODEL_DIRECTORY}' directories found under ${root}." >&2
    echo "" >&2
    echo "Matches:" >&2
    local m
    for m in "${found[@]}"; do
      echo "  - ${m}" >&2
    done
    echo "" >&2
    echo "Possible fixes:" >&2
    echo "  1. Set repository_directory / project_directory / model_directory in deployment/config.yaml" >&2
    echo "  2. Remove unused copies of current_model" >&2
    echo "  3. Point application_directory at the intended install root" >&2
    return 2
  fi
  DISCOVERED_MODEL_ROOT="${found[0]}"
  return 0
}

_derive_from_model_root() {
  # MODEL_ROOT = .../<project>/<model>
  MODEL_ROOT="${DISCOVERED_MODEL_ROOT}"
  PROJECT_ROOT="$(cd "${MODEL_ROOT}/.." && pwd)"
  # Repository root = nearest ancestor containing .git, else parent of project
  local cursor="${PROJECT_ROOT}"
  REPOSITORY_ROOT=""
  while [[ "${cursor}" != "/" ]]; do
    if [[ -d "${cursor}/.git" ]]; then
      REPOSITORY_ROOT="${cursor}"
      break
    fi
    cursor="$(cd "${cursor}/.." && pwd)"
  done
  if [[ -z "${REPOSITORY_ROOT}" ]]; then
    REPOSITORY_ROOT="$(cd "${PROJECT_ROOT}/.." && pwd)"
  fi
}

_apply_configured_layout() {
  # Build expected paths from config (may not exist yet — fresh install)
  if [[ -n "${REPOSITORY_DIRECTORY}" ]]; then
    REPOSITORY_ROOT="$(_path_join "${APPLICATION_DIRECTORY}" "${REPOSITORY_DIRECTORY}")"
    PROJECT_ROOT="$(_path_join "${REPOSITORY_ROOT}" "${PROJECT_DIRECTORY}")"
  else
    # Mode A: project package lives directly under application_directory
    # Also supports: application_directory IS the git root containing project_directory
    local direct_project candidate_repo
    direct_project="$(_path_join "${APPLICATION_DIRECTORY}" "${PROJECT_DIRECTORY}")"
    if [[ -d "${direct_project}" ]] || [[ ! -d "${APPLICATION_DIRECTORY}/.git" ]]; then
      REPOSITORY_ROOT="${APPLICATION_DIRECTORY}"
      PROJECT_ROOT="${direct_project}"
    else
      # application_directory itself is a git checkout that may BE the project
      REPOSITORY_ROOT="${APPLICATION_DIRECTORY}"
      if _is_project_root "${APPLICATION_DIRECTORY}"; then
        PROJECT_ROOT="${APPLICATION_DIRECTORY}"
      else
        PROJECT_ROOT="${direct_project}"
      fi
    fi
  fi
  MODEL_ROOT="$(_path_join "${PROJECT_ROOT}" "${MODEL_DIRECTORY}")"
}

_finalize_derived_paths() {
  VENV_DIR="$(_path_join "${MODEL_ROOT}" "${VIRTUAL_ENVIRONMENT_NAME}")"
  VENV_BIN="$(_path_join "${VENV_DIR}" "bin")"
  GUNICORN_CONF="$(_path_join "${PROJECT_ROOT}" "deployment/gunicorn/gunicorn.conf.py")"
  NGINX_CONF_SRC="$(_path_join "${PROJECT_ROOT}" "deployment/nginx/${NGINX_SITE_NAME}.conf")"
  SYSTEMD_UNIT_SRC="$(_path_join "${PROJECT_ROOT}" "deployment/systemd/${GUNICORN_SERVICE_NAME}.service")"

  # Back-compat aliases used by older script snippets / docs
  APP_ROOT="${PROJECT_ROOT}"
  REPO_ROOT="${REPOSITORY_ROOT}"
  MODEL_SUBDIRECTORY="${MODEL_DIRECTORY}"
  APP_SUBDIRECTORY="${PROJECT_DIRECTORY}"
}

_diagnose_missing_model() {
  echo "" >&2
  echo "ERROR: Unable to locate '${MODEL_DIRECTORY}' (model root)." >&2
  echo "" >&2
  echo "Searched under:" >&2
  echo "  ${APPLICATION_DIRECTORY}" >&2
  echo "" >&2
  echo "Configured layout would be:" >&2
  echo "  REPOSITORY_ROOT = ${REPOSITORY_ROOT:-"(unset)"}" >&2
  echo "  PROJECT_ROOT    = ${PROJECT_ROOT:-"(unset)"}" >&2
  echo "  MODEL_ROOT      = ${MODEL_ROOT:-"(unset)"}" >&2
  echo "" >&2
  echo "Detected directories (depth ≤ 4):" >&2
  if [[ -d "${APPLICATION_DIRECTORY}" ]]; then
    find "${APPLICATION_DIRECTORY}" -maxdepth 4 -type d \( -name ".git" -o -name "Steel-Beam-Estimation" -o -name "SteelBeamEstimator" -o -name "current_model" \) 2>/dev/null \
      | sed 's/^/  - /' >&2 || echo "  (none)" >&2
  else
    echo "  (application_directory does not exist yet)" >&2
  fi
  echo "" >&2
  echo "Possible fixes:" >&2
  echo "  1. Set repository_directory / project_directory / model_directory in deployment/config.yaml" >&2
  echo "  2. For monorepo installs use repository_directory: SteelBeamEstimator" >&2
  echo "  3. Run 02_clone_project.sh if the repository has not been cloned yet" >&2
  echo "  4. Ensure application_directory points at the install root (e.g. /opt/steel-beam-estimation)" >&2
}

# ── Main resolution ──────────────────────────────────────────────────────────

resolve_paths() {
  load_config_keys

  APPLICATION_DIRECTORY="${APPLICATION_DIRECTORY%/}"
  DEPLOYMENT_MODE="Fresh Install"
  DISCOVERED_MODEL_ROOT=""

  _apply_configured_layout

  # If configured MODEL_ROOT already exists and looks valid — use it (Existing or Fresh after clone)
  if [[ -d "${MODEL_ROOT}" ]] && _is_model_root "${MODEL_ROOT}"; then
    if [[ -d "${PROJECT_ROOT}/.git" ]] || [[ -d "${REPOSITORY_ROOT}/.git" ]]; then
      DEPLOYMENT_MODE="Existing Install"
    else
      DEPLOYMENT_MODE="Configured Layout"
    fi
    _finalize_derived_paths
    return 0
  fi

  # Auto-discover under application_directory when configured path missing
  if [[ -d "${APPLICATION_DIRECTORY}" ]]; then
    local rc=0
    DISCOVERED_MODEL_ROOT=""
    _discover_current_model_dirs "${APPLICATION_DIRECTORY}" || rc=$?
    if [[ ${rc} -eq 2 ]]; then
      exit 1
    fi
    if [[ ${rc} -eq 0 && -n "${DISCOVERED_MODEL_ROOT}" ]]; then
      _derive_from_model_root
      DEPLOYMENT_MODE="Existing Install (auto-detected)"
      _finalize_derived_paths
      return 0
    fi
  fi

  # Also try discovering relative to this checked-out package (scripts run from git tree)
  if _is_project_root "${PACKAGE_DIR}"; then
    PROJECT_ROOT="${PACKAGE_DIR}"
    MODEL_ROOT="$(_path_join "${PROJECT_ROOT}" "${MODEL_DIRECTORY}")"
    local cursor="${PROJECT_ROOT}"
    REPOSITORY_ROOT="${PROJECT_ROOT}"
    while [[ "${cursor}" != "/" ]]; do
      if [[ -d "${cursor}/.git" ]]; then
        REPOSITORY_ROOT="${cursor}"
        break
      fi
      cursor="$(cd "${cursor}/.." && pwd)"
    done
    if [[ -d "${MODEL_ROOT}" ]] && _is_model_root "${MODEL_ROOT}"; then
      DEPLOYMENT_MODE="Existing Install (package-local)"
      _finalize_derived_paths
      return 0
    fi
  fi

  # Fresh install: keep configured paths even if they do not exist yet
  DEPLOYMENT_MODE="Fresh Install"
  _finalize_derived_paths
}

require_model_root() {
  if [[ ! -d "${MODEL_ROOT}" ]] || ! _is_model_root "${MODEL_ROOT}"; then
    _diagnose_missing_model
    exit 1
  fi
}

require_project_root() {
  if [[ ! -d "${PROJECT_ROOT}" ]] || ! _is_project_root "${PROJECT_ROOT}"; then
    echo "" >&2
    echo "ERROR: Unable to locate project root (expected deployment/ + ${MODEL_DIRECTORY}/)." >&2
    echo "  PROJECT_ROOT=${PROJECT_ROOT:-"(unset)"}" >&2
    echo "" >&2
    echo "Possible fixes:" >&2
    echo "  1. Run 02_clone_project.sh" >&2
    echo "  2. Correct project_directory in deployment/config.yaml" >&2
    echo "  3. Rely on auto-discovery by placing a single current_model under application_directory" >&2
    exit 1
  fi
}

print_deployment_summary() {
  echo "========================================="
  echo "Deployment Configuration"
  echo "========================================="
  echo ""
  echo "Package version:       ${DEPLOYMENT_PACKAGE_VERSION}"
  echo "Application Directory: ${APPLICATION_DIRECTORY}"
  echo "Repository Root:       ${REPOSITORY_ROOT}"
  echo "Project Root:          ${PROJECT_ROOT}"
  echo "Model Root:            ${MODEL_ROOT}"
  echo "Virtual Environment:   ${VENV_DIR}"
  echo "Gunicorn bind:         ${GUNICORN_BIND}"
  echo "GitHub repository:     ${GITHUB_REPOSITORY}"
  echo "Branch:                ${BRANCH}"
  echo ""
  echo "Deployment Mode:       ${DEPLOYMENT_MODE}"
  echo ""
  if [[ -d "${MODEL_ROOT}" ]] && _is_model_root "${MODEL_ROOT}"; then
    echo "Resolved successfully (model root present)"
  elif [[ "${DEPLOYMENT_MODE}" == "Fresh Install" ]]; then
    echo "Resolved for fresh install (paths configured; model root not present yet)"
  else
    echo "Resolved with warnings (model root missing)"
  fi
  echo "========================================="
}

# ── Bootstrap on source ──────────────────────────────────────────────────────

load_config_keys
resolve_paths

# Optional: DEPLOY_QUIET=1 skips summary (used by helpers sourced repeatedly)
if [[ "${DEPLOY_QUIET:-0}" != "1" && "${DEPLOY_SKIP_SUMMARY:-0}" != "1" ]]; then
  # Only print once per top-level script invocation
  if [[ -z "${_STEEL_DEPLOY_SUMMARY_SHOWN:-}" ]]; then
    export _STEEL_DEPLOY_SUMMARY_SHOWN=1
    print_deployment_summary
    echo ""
  fi
fi
