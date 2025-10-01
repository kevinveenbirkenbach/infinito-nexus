#!/bin/sh
set -euo pipefail

log() { printf '%s %s\n' "[entrypoint]" "$*" >&2; }

# --- Simple boolean normalization --------------------------------------------
bool_norm () {
  v="$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')"
  case "$v" in
    1|true|yes|on)  echo "true" ;;
    0|false|no|off|"") echo "false" ;;
    *) echo "false" ;;
  esac
}

# Expected ENV (from env.j2)
MAINTENANCE="$(bool_norm "${ESPO_INIT_MAINTENANCE_MODE:-false}")"
CRON_DISABLED="$(bool_norm "${ESPO_INIT_CRON_DISABLED:-false}")"
USE_CACHE="$(bool_norm "${ESPO_INIT_USE_CACHE:-true}")"

APP_DIR="/var/www/html"
SET_FLAGS_SCRIPT="${ESPOCRM_SET_FLAGS_SCRIPT}"

# --- Wait for bootstrap.php (max 60s, e.g. fresh volume) ----------------------
log "Waiting for ${APP_DIR}/bootstrap.php..."
for i in $(seq 1 60); do
  [ -f "${APP_DIR}/bootstrap.php" ] && break
  sleep 1
done
if [ ! -f "${APP_DIR}/bootstrap.php" ]; then
  log "ERROR: bootstrap.php missing after 60s"; exit 1
fi

# --- Apply config flags via set_flags.php ------------------------------------
log "Applying runtime flags via set_flags.php..."
php "${SET_FLAGS_SCRIPT}"

# --- Clear cache (safe) -------------------------------------------------------
php "${APP_DIR}/clear_cache.php" || true

# --- Hand off to CMD ----------------------------------------------------------
if [ "$#" -gt 0 ]; then
  log "Exec CMD: $*"
  exec "$@"
fi

# Try common server commands
for cmd in apache2-foreground httpd-foreground php-fpm php-fpm8.3 php-fpm8.2 supervisord; do
  if command -v "$cmd" >/dev/null 2>&1; then
    log "Starting: $cmd"
    case "$cmd" in
      php-fpm|php-fpm8.*) exec "$cmd" -F ;;
      supervisord)        exec "$cmd" -n ;;
      *)                  exec "$cmd" ;;
    esac
  fi
done

log "No known server command found; tailing to keep container alive."
exec tail -f /dev/null
