#!/usr/bin/env bash
# 01_server_setup.sh — Base OS packages (Phase D.4.1)
# Idempotent. Does NOT deploy the application.

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

require_root_or_sudo
require_cmd apt-get

info "Updating apt indexes"
${SUDO} apt-get update -y

info "Installing base packages (python${PYTHON_VERSION}, git, nginx, …)"
${SUDO} DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates \
  curl \
  git \
  build-essential \
  "python${PYTHON_VERSION}" \
  "python${PYTHON_VERSION}-venv" \
  python3-pip \
  nginx \
  ufw || warn "Some packages may already be present or python${PYTHON_VERSION} unavailable"

if ! command -v "python${PYTHON_VERSION}" >/dev/null 2>&1; then
  warn "python${PYTHON_VERSION} not found; ensuring python3 exists"
  require_cmd python3
fi

info "Creating application directory: ${APPLICATION_DIRECTORY}"
${SUDO} mkdir -p "${APPLICATION_DIRECTORY}"
${SUDO} chown "${SSH_USER}:${SSH_USER}" "${APPLICATION_DIRECTORY}" || \
  warn "Could not chown to ${SSH_USER}; adjust ownership manually"

info "Server setup complete"
