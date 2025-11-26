#!/bin/sh
# Minimal SuiteCRM entrypoint for Infinito.Nexus
set -eu

APP_DIR="/var/www/html"
WEB_USER="www-data"
WEB_GROUP="www-data"

log() { printf '%s %s\n' "[suitecrm-entrypoint]" "$*" >&2; }

# Ensure application directory exists
if [ ! -d "$APP_DIR" ]; then
  log "ERROR: Application directory '$APP_DIR' does not exist."
  exit 1
fi

# Fix permissions (best-effort, idempotent enough for small instances)
log "Adjusting permissions on ${APP_DIR} (this may take some time on first run)..."
chown -R "$WEB_USER:$WEB_GROUP" "$APP_DIR"
find "$APP_DIR" -type d -exec chmod 755 {} \;
find "$APP_DIR" -type f -exec chmod 644 {} \;

# Writable directories
for d in cache custom modules themes upload; do
  if [ -d "${APP_DIR}/${d}" ]; then
    chmod -R 775 "${APP_DIR}/${d}"
  fi
done

# Add a simple healthcheck file
echo "OK" > "${APP_DIR}/healthcheck.html"
chown "$WEB_USER:$WEB_GROUP" "${APP_DIR}/healthcheck.html"

# (Optional) place for future auto-config (DB, LDAP, OIDC) by editing config.php

# Hand off to CMD (Apache in foreground by default)
if [ "$#" -gt 0 ]; then
  log "Executing CMD: $*"
  exec "$@"
fi

# Default: start Apache HTTPD in foreground
if command -v apache2-foreground >/dev/null 2>&1; then
  log "Starting apache2-foreground..."
  exec apache2-foreground
fi

log "No known server command found; keeping container alive."
exec tail -f /dev/null
