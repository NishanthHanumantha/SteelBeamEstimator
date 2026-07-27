#!/usr/bin/env bash
# 10_update_application.sh — Pull latest GitHub branch and refresh app (Phase D.4)
# Idempotent: fetch + ff-only pull; reinstall requirements; restart services.
# Does NOT force-reset local changes (fail-safe).

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

require_cmd git

REPO_DIR="${APPLICATION_DIRECTORY}"
if [[ ! -d "${REPO_DIR}/.git" ]]; then
  # Flat package may live at APPLICATION_DIRECTORY; monorepo root is APPLICATION_DIRECTORY
  die "No git repository at ${REPO_DIR}. Run 02_clone_project.sh first."
fi

info "Updating repository on branch ${BRANCH}"
git -C "${REPO_DIR}" fetch --all --prune
git -C "${REPO_DIR}" checkout "${BRANCH}"
if ! git -C "${REPO_DIR}" pull --ff-only origin "${BRANCH}"; then
  die "Fast-forward pull failed. Commit/stash server-side changes or resolve conflicts, then retry."
fi

# Refresh deps + validate + restart if helpers exist
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
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
info "Rollback: git -C ${REPO_DIR} checkout <previous-sha> && re-run 04 + 09"
