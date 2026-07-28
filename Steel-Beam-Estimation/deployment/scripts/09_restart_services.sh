#!/usr/bin/env bash
# 09_restart_services.sh — Restart gunicorn + nginx; probe /health (Phase D.4.1)

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"
require_root_or_sudo

info "Restarting ${GUNICORN_SERVICE_NAME}"
if ${SUDO} systemctl cat "${GUNICORN_SERVICE_NAME}" >/dev/null 2>&1; then
  ${SUDO} systemctl restart "${GUNICORN_SERVICE_NAME}"
  ${SUDO} systemctl --no-pager --full status "${GUNICORN_SERVICE_NAME}" | head -n 20 || true
else
  die "systemd unit ${GUNICORN_SERVICE_NAME} not installed. Run 07_install_gunicorn.sh first."
fi

info "Reloading nginx"
if ${SUDO} systemctl cat nginx >/dev/null 2>&1; then
  if ${SUDO} nginx -t; then
    ${SUDO} systemctl reload nginx
  else
    die "nginx -t failed — not reloading"
  fi
else
  warn "nginx service not found — skip reload"
fi

info "Checking /health via ${GUNICORN_BIND}"
if command -v curl >/dev/null 2>&1; then
  if curl -fsS "http://${GUNICORN_BIND}/health" | head -c 400; then
    echo
    info "Health check OK"
  else
    warn "Health check failed — inspect: journalctl -u ${GUNICORN_SERVICE_NAME}"
  fi
else
  warn "curl not installed — skip health probe"
fi

info "Service restart complete"
