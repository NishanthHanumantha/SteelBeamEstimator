#!/usr/bin/env bash
# 02_clone_project.sh — Clone or update the GitHub repository (Phase D.4)
# Idempotent: clones once; subsequent runs fetch + checkout branch.

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

require_cmd git
[[ -n "${GITHUB_REPOSITORY}" ]] || die "github_repository is empty in deployment/config.yaml"

info "Ensuring parent directory exists: ${APPLICATION_DIRECTORY}"
mkdir -p "${APPLICATION_DIRECTORY}"

TARGET="${APPLICATION_DIRECTORY}"
# Repo may already be the application_directory contents, or nested.
# Convention: clone into APPLICATION_DIRECTORY as the repo root.
if [[ -d "${TARGET}/.git" ]]; then
  info "Repository already present — fetching ${BRANCH}"
  git -C "${TARGET}" fetch --all --prune
  git -C "${TARGET}" checkout "${BRANCH}"
  git -C "${TARGET}" pull --ff-only origin "${BRANCH}" || \
    warn "ff-only pull failed; resolve locally before continuing"
else
  # If directory is non-empty without .git, clone into a temp then fail safely
  if [[ -n "$(ls -A "${TARGET}" 2>/dev/null || true)" ]]; then
    die "Directory ${TARGET} is not empty and is not a git repo. Aborting to avoid overwrite."
  fi
  info "Cloning ${GITHUB_REPOSITORY} (branch ${BRANCH}) into ${TARGET}"
  git clone --branch "${BRANCH}" --single-branch "${GITHUB_REPOSITORY}" "${TARGET}"
fi

# Prefer monorepo layout: Steel-Beam-Estimation under repo root
if [[ ! -d "${APP_ROOT}" ]]; then
  # Fallback: APPLICATION_DIRECTORY IS the Steel-Beam-Estimation package
  if [[ -d "${TARGET}/current_model" ]]; then
    warn "Using flat layout (current_model under ${TARGET})"
  else
    die "Could not find ${APP_ROOT} or ${TARGET}/current_model after clone"
  fi
fi

info "Clone/update complete"
info "  APP_ROOT=${APP_ROOT}"
info "  MODEL_ROOT=${MODEL_ROOT}"
