#!/bin/sh
# POSIX-safe entrypoint for EspoCRM container
# Compatible with /bin/sh (dash/busybox). Avoids 'pipefail' and non-portable features.
set -eu

log() { printf '%s %s\n' "[entrypoint]" "$*" >&2; }

# --- Simple boolean normalization --------------------------------------------
bool_norm () {
  v="$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]' 2>/dev/null || true)"
  case "$v" in
    1|true|yes|on)  echo "true" ;;
    0|false|no|off|"") echo "false" ;;
    *) echo "false" ;;
  esac
}

# --- Environment initialization ----------------------------------------------
MAINTENANCE="$(bool_norm "${ESPO_INIT_MAINTENANCE_MODE:-false}")"
CRON_DISABLED="$(bool_norm "${ESPO_INIT_CRON_DISABLED:-false}")"
USE_CACHE="$(bool_norm "${ESPO_INIT_USE_CACHE:-true}")"

APP_DIR="/var/www/html"

# Provided by env.j2 (fallback ensures robustness)
SET_FLAGS_SCRIPT="${ESPOCRM_SET_FLAGS_SCRIPT:-/usr/local/bin/set_flags.php}"
if [ ! -f "$SET_FLAGS_SCRIPT" ]; then
  log "WARN: SET_FLAGS_SCRIPT '$SET_FLAGS_SCRIPT' not found; falling back to /usr/local/bin/set_flags.php"
  SET_FLAGS_SCRIPT="/usr/local/bin/set_flags.php"
fi

# --- Wait for bootstrap.php (max 60s, e.g. fresh volume) ----------------------
log "Waiting for ${APP_DIR}/bootstrap.php..."
count=0
while [ $count -lt 60 ] && [ ! -f "${APP_DIR}/bootstrap.php" ]; do
  sleep 1
  count=$((count + 1))
done
if [ ! -f "${APP_DIR}/bootstrap.php" ]; then
  log "ERROR: bootstrap.php missing after 60s"
  exit 1
fi

# --- Apply config flags via set_flags.php ------------------------------------
log "Applying runtime flags via set_flags.php..."
if ! php "${SET_FLAGS_SCRIPT}"; then
  log "ERROR: set_flags.php execution failed"
  exit 1
fi

# --- Clear cache (safe) -------------------------------------------------------
if php "${APP_DIR}/clear_cache.php" 2>/dev/null; then
  log "Cache cleared successfully."
else
  log "WARN: Cache clearing skipped or failed (non-critical)."
fi

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

# --- Fallback ---------------------------------------------------------------
log "No known server command found; tailing to keep container alive."
exec tail -f /dev/null
