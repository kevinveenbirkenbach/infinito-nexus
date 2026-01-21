#!/bin/sh
# POSIX-safe entrypoint for EspoCRM container
# Runs the original image entrypoint first, then applies custom patching logic.
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

# --- Run original image entrypoint FIRST -------------------------------------
ORIG_ENTRYPOINT="/usr/local/bin/docker-entrypoint.sh"

if [ -x "$ORIG_ENTRYPOINT" ]; then
  log "Running original entrypoint: $ORIG_ENTRYPOINT $*"
  # IMPORTANT:
  # - We run it with the same arguments we received.
  # - The original entrypoint may create/copy webroot and do first-start init.
  "$ORIG_ENTRYPOINT" "$@"
else
  log "WARN: original entrypoint not found/executable at $ORIG_ENTRYPOINT (skipping)"
fi

# --- Environment initialization ----------------------------------------------
MAINTENANCE="$(bool_norm "${ESPOCRM_SEED_MAINTENANCE_MODE:-}")"
CRON_DISABLED="$(bool_norm "${ESPOCRM_SEED_CRON_DISABLED:-}")"
USE_CACHE="$(bool_norm "${ESPOCRM_SEED_USE_CACHE:-}")"


log "Flags: maintenance=${MAINTENANCE} cron_disabled=${CRON_DISABLED} use_cache=${USE_CACHE}"
APP_DIR="/var/www/html"

# Provided by env.j2
: "${ESPOCRM_SCRIPT_SEED:?missing ESPOCRM_SCRIPT_SEED}"
SEED_CONFIG_SCRIPT="${ESPOCRM_SCRIPT_SEED}"

# --- Guard: bootstrap.php must exist NOW (original entrypoint should have made it) ---
if [ ! -f "${APP_DIR}/bootstrap.php" ]; then
  log "ERROR: ${APP_DIR}/bootstrap.php is missing after original entrypoint ran."
  log "Hint: You are probably mounting a volume over /var/www/html instead of only /var/www/html/data, /custom, /client/custom."
  exit 1
fi

# --- Apply config flags via seed_config.php -----------------------------------
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
# At this point, the original entrypoint already ran. We still need to run the actual server process.
# If a command was passed, run it. Otherwise, try common server commands.
if [ "$#" -gt 0 ]; then
  log "Exec CMD: $*"
  exec "$@"
fi

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
