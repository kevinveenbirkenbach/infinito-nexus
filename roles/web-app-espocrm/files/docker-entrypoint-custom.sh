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
MAINTENANCE="$(bool_norm "${ESPOCRM_SEED_MAINTENANCE_MODE}")"
CRON_DISABLED="$(bool_norm "${ESPOCRM_SEED_CRON_DISABLED}")"
USE_CACHE="$(bool_norm "${ESPOCRM_SEED_USE_CACHE}")"

APP_DIR="/var/www/html"

# Provided by env.j2 (fallback ensures robustness)
SEED_CONFIG_SCRIPT="${ESPOCRM_SCRIPT_SEED}"

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

# --- Apply config flags via seed_config.php ------------------------------------
log "Applying runtime flags via seed_config.php..."
if ! php "${SEED_CONFIG_SCRIPT}"; then
  log "ERROR: seed_config.php execution failed"
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
