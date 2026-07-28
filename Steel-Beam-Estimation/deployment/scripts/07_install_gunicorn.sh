#!/usr/bin/env bash
# 07_install_gunicorn.sh — Install gunicorn + render systemd unit (Phase D.4.1)

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"
require_root_or_sudo

require_project_root
require_model_root
[[ -x "${VENV_BIN}/pip" ]] || die "Virtualenv missing at ${VENV_DIR}. Run 03_create_venv.sh first."
[[ -f "${GUNICORN_CONF}" ]] || die "Missing gunicorn config: ${GUNICORN_CONF}"
[[ -f "${SYSTEMD_UNIT_SRC}" ]] || die "Missing systemd unit: ${SYSTEMD_UNIT_SRC}"

info "Ensuring gunicorn is installed in venv"
"${VENV_BIN}/pip" install "gunicorn>=22.0,<24"

UNIT_DST="/etc/systemd/system/${GUNICORN_SERVICE_NAME}.service"
TMP_UNIT="$(mktemp)"

info "Rendering systemd unit → ${UNIT_DST}"
sed \
  -e "s|__APP_USER__|${SSH_USER}|g" \
  -e "s|__MODEL_ROOT__|${MODEL_ROOT}|g" \
  -e "s|__VENV_BIN__|${VENV_BIN}|g" \
  -e "s|__GUNICORN_CONF__|${GUNICORN_CONF}|g" \
  -e "s|__GUNICORN_BIND__|${GUNICORN_BIND}|g" \
  "${SYSTEMD_UNIT_SRC}" > "${TMP_UNIT}"

${SUDO} cp "${TMP_UNIT}" "${UNIT_DST}"
rm -f "${TMP_UNIT}"
${SUDO} systemctl daemon-reload
${SUDO} systemctl enable "${GUNICORN_SERVICE_NAME}" || warn "enable failed — check unit file"

info "Gunicorn/systemd install complete (not started by this script)"
info "Start with: sudo systemctl start ${GUNICORN_SERVICE_NAME}"
