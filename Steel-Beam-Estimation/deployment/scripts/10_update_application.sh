#!/usr/bin/env bash
# 10_update_application.sh — Pull branch, refresh deps, restart (Phase D.4.1)
# Uses REPOSITORY_ROOT from _common.sh (works for nested monorepo installs).

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

require_cmd git

if [[ ! -d "${REPOSITORY_ROOT}/.git" ]]; then
  echo "" >&2
  echo "ERROR: No git repository at REPOSITORY_ROOT=${REPOSITORY_ROOT}" >&2
  echo "" >&2
  echo "Possible fixes:" >&2
  echo "  1. Run 02_clone_project.sh" >&2
  echo "  2. Set repository_directory so REPOSITORY_ROOT points at the clone" >&2
  echo "  3. For auto-detect, ensure a single current_model exists under application_directory" >&2
  exit 1
fi

info "Updating repository at ${REPOSITORY_ROOT} (branch ${BRANCH})"
git -C "${REPOSITORY_ROOT}" fetch --all --prune
git -C "${REPOSITORY_ROOT}" checkout "${BRANCH}"
if ! git -C "${REPOSITORY_ROOT}" pull --ff-only origin "${BRANCH}"; then
  die "Fast-forward pull failed. Commit/stash server-side changes or resolve conflicts, then retry."
fi

# Refresh resolved paths after pull
DEPLOY_SKIP_SUMMARY=1
unset _STEEL_DEPLOY_SUMMARY_SHOWN
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_common.sh"

info "Reinstalling requirements"
bash "${SCRIPT_DIR}/04_install_requirements.sh"

info "Validating application"
bash "${SCRIPT_DIR}/06_validate_application.sh" || warn "Validation reported issues"

if [[ "${EUID}" -eq 0 ]] || command -v sudo >/dev/null 2>&1; then
  info "Restarting services"
  bash "${SCRIPT_DIR}/09_restart_services.sh" || warn "Restart failed — run 09 manually"
else
  warn "No sudo — skip service restart; run 09_restart_services.sh as an admin"
fi

info "Application update complete"
info "Rollback: git -C ${REPOSITORY_ROOT} checkout <previous-sha> && re-run 04 + 09"
