#!/usr/bin/env bash
# 08_install_nginx.sh — Install nginx site config for Steel Beam Estimator (Phase D.4)
# Idempotent: rewrites site file from template; reloads nginx only if test passes.

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"
require_root_or_sudo
require_cmd nginx

if [[ ! -d "${MODEL_ROOT}" && -d "${APPLICATION_DIRECTORY}/current_model" ]]; then
  MODEL_ROOT="${APPLICATION_DIRECTORY}/current_model"
  APP_ROOT="${APPLICATION_DIRECTORY}"
  NGINX_CONF_SRC="${APP_ROOT}/deployment/nginx/${NGINX_SITE_NAME}.conf"
fi

[[ -f "${NGINX_CONF_SRC}" ]] || die "Missing nginx template: ${NGINX_CONF_SRC}"

SERVER_NAME="${SERVER_NAME_OVERRIDE:-_}"
UPSTREAM="${GUNICORN_BIND}"

AVAILABLE="/etc/nginx/sites-available/${NGINX_SITE_NAME}.conf"
ENABLED="/etc/nginx/sites-enabled/${NGINX_SITE_NAME}.conf"
TMP_CONF="$(mktemp)"

info "Rendering nginx site ${AVAILABLE}"
sed \
  -e "s|__SERVER_NAME__|${SERVER_NAME}|g" \
  -e "s|__APP_ROOT__|${APP_ROOT}|g" \
  -e "s|__GUNICORN_UPSTREAM__|${UPSTREAM}|g" \
  "${NGINX_CONF_SRC}" > "${TMP_CONF}"

${SUDO} cp "${TMP_CONF}" "${AVAILABLE}"
rm -f "${TMP_CONF}"

# Enable site (idempotent symlink)
${SUDO} mkdir -p /etc/nginx/sites-enabled
${SUDO} ln -sfn "${AVAILABLE}" "${ENABLED}"

# Disable default site if present (optional, fail-safe)
if [[ -L /etc/nginx/sites-enabled/default ]]; then
  info "Removing default nginx site symlink"
  ${SUDO} rm -f /etc/nginx/sites-enabled/default
fi

info "Testing nginx configuration"
if ${SUDO} nginx -t; then
  ${SUDO} systemctl reload nginx || ${SUDO} systemctl restart nginx
  info "Nginx reloaded"
else
  die "nginx -t failed — previous config left in place where possible; fix template and re-run"
fi

info "Nginx site install complete: ${NGINX_SITE_NAME}"
