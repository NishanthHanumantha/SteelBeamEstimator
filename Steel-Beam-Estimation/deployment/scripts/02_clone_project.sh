#!/usr/bin/env bash
# 02_clone_project.sh — Clone or update GitHub repository (Phase D.4.1)
#
# Cases:
#   1. Git repo already at REPOSITORY_ROOT → fetch + ff-only pull
#   2. REPOSITORY_ROOT missing / empty → clone
#   3. Directory has unrelated non-git content → abort safely
#   4. Git repo with different remote → warn and exit safely

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

require_cmd git
[[ -n "${GITHUB_REPOSITORY}" ]] || die "github_repository is empty in deployment/config.yaml"

normalize_remote() {
  # Strip .git suffix and trailing slash for comparison
  echo "$1" | sed -E 's#\.git$##; s#/$##'
}

EXPECTED_REMOTE="$(normalize_remote "${GITHUB_REPOSITORY}")"
TARGET="${REPOSITORY_ROOT}"

info "Repository target: ${TARGET}"
mkdir -p "$(dirname "${TARGET}")"

if [[ -d "${TARGET}/.git" ]]; then
  CURRENT_REMOTE="$(git -C "${TARGET}" remote get-url origin 2>/dev/null || true)"
  CURRENT_NORM="$(normalize_remote "${CURRENT_REMOTE}")"
  if [[ -n "${CURRENT_REMOTE}" && "${CURRENT_NORM}" != "${EXPECTED_REMOTE}" ]]; then
    echo "" >&2
    echo "ERROR: Repository exists but origin remote differs." >&2
    echo "  Path:     ${TARGET}" >&2
    echo "  Expected: ${GITHUB_REPOSITORY}" >&2
    echo "  Found:    ${CURRENT_REMOTE}" >&2
    echo "" >&2
    echo "Possible fixes:" >&2
    echo "  1. Update github_repository in deployment/config.yaml" >&2
    echo "  2. Change origin: git -C ${TARGET} remote set-url origin <url>" >&2
    echo "  3. Use a different application_directory / repository_directory" >&2
    exit 1
  fi

  info "Repository already present — updating branch ${BRANCH}"
  git -C "${TARGET}" fetch --all --prune
  git -C "${TARGET}" checkout "${BRANCH}"
  if ! git -C "${TARGET}" pull --ff-only origin "${BRANCH}"; then
    die "Fast-forward pull failed. Resolve/stash local commits on the server, then retry."
  fi
  info "Repository updated"
elif [[ -e "${TARGET}" ]]; then
  # Exists but not a git repo
  if [[ -n "$(ls -A "${TARGET}" 2>/dev/null || true)" ]]; then
    echo "" >&2
    echo "ERROR: ${TARGET} exists, is not empty, and is not a git repository." >&2
    echo "Refusing to overwrite unrelated files." >&2
    echo "" >&2
    echo "Possible fixes:" >&2
    echo "  1. Point repository_directory at the existing clone" >&2
    echo "  2. Remove or relocate unrelated files in ${TARGET}" >&2
    echo "  3. Clone manually, then re-run this script" >&2
    exit 1
  fi
  info "Cloning ${GITHUB_REPOSITORY} (branch ${BRANCH}) into empty ${TARGET}"
  git clone --branch "${BRANCH}" --single-branch "${GITHUB_REPOSITORY}" "${TARGET}"
else
  info "Cloning ${GITHUB_REPOSITORY} (branch ${BRANCH}) into ${TARGET}"
  git clone --branch "${BRANCH}" --single-branch "${GITHUB_REPOSITORY}" "${TARGET}"
fi

# Re-resolve paths after clone (model may now exist)
DEPLOY_SKIP_SUMMARY=1
unset _STEEL_DEPLOY_SUMMARY_SHOWN
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_common.sh"

if [[ ! -d "${PROJECT_ROOT}" ]]; then
  echo "" >&2
  echo "ERROR: After clone, project root was not found." >&2
  echo "  Expected PROJECT_ROOT=${PROJECT_ROOT}" >&2
  echo "  REPOSITORY_ROOT=${REPOSITORY_ROOT}" >&2
  echo "" >&2
  echo "Possible fixes:" >&2
  echo "  1. Set project_directory to the folder that contains current_model/ (usually Steel-Beam-Estimation)" >&2
  echo "  2. Set repository_directory correctly for monorepo checkouts (e.g. SteelBeamEstimator)" >&2
  exit 1
fi

info "Clone/update complete"
info "  REPOSITORY_ROOT=${REPOSITORY_ROOT}"
info "  PROJECT_ROOT=${PROJECT_ROOT}"
info "  MODEL_ROOT=${MODEL_ROOT}"
