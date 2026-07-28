#!/usr/bin/env bash
# 08_install_nginx.sh — Install nginx site from template (Phase D.4.1)

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"
require_root_or_sudo
require_cmd nginx

require_project_root
[[ -f "${NGINX_CONF_SRC}" ]] || die "Missing nginx template: ${NGINX_CONF_SRC}"

SERVER_NAME="${SERVER_NAME_OVERRIDE:-_}"
UPSTREAM="${GUNICORN_BIND}"

AVAILABLE="/etc/nginx/sites-available/${NGINX_SITE_NAME}.conf"
ENABLED="/etc/nginx/sites-enabled/${NGINX_SITE_NAME}.conf"
TMP_CONF="$(mktemp)"

info "Rendering nginx site → ${AVAILABLE}"
info "  APP/PROJECT_ROOT=${PROJECT_ROOT}"
info "  upstream=${UPSTREAM}"

sed \
  -e "s|__SERVER_NAME__|${SERVER_NAME}|g" \
  -e "s|__APP_ROOT__|${PROJECT_ROOT}|g" \
  -e "s|__GUNICORN_UPSTREAM__|${UPSTREAM}|g" \
  "${NGINX_CONF_SRC}" > "${TMP_CONF}"

${SUDO} cp "${TMP_CONF}" "${AVAILABLE}"
rm -f "${TMP_CONF}"

${SUDO} mkdir -p /etc/nginx/sites-enabled
${SUDO} ln -sfn "${AVAILABLE}" "${ENABLED}"

if [[ -L /etc/nginx/sites-enabled/default ]]; then
  info "Removing default nginx site symlink"
  ${SUDO} rm -f /etc/nginx/sites-enabled/default
fi

info "Testing nginx configuration"
if ${SUDO} nginx -t; then
  ${SUDO} systemctl reload nginx || ${SUDO} systemctl restart nginx
  info "Nginx reloaded"
else
  die "nginx -t failed — fix template and re-run"
fi

info "Nginx site install complete: ${NGINX_SITE_NAME}"
