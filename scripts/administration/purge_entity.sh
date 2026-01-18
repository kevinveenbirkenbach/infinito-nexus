#!/usr/bin/env bash
# purge_entity.sh
#
# Usage:
#   ./purge_entity.sh <STACK1> [STACK2] [STACK3] ...
#
# Example:
#   ./purge_entity.sh keycloak openldap nextcloud
#
# What it does per stack:
#   - (Optional) Drops the app database if detected (postgres/mariadb)
#   - docker compose down
#   - removes /opt/docker/<STACK>/volumes
#   - removes /opt/docker/<STACK>

set -euo pipefail

if [[ "$#" -lt 1 ]]; then
  echo "ERROR: No stack names provided."
  echo "Usage: $0 <STACK1> [STACK2] [STACK3] ..."
  exit 2
fi

log()  { echo ">>> $*"; }
warn() { echo "!!! WARNING: $*" >&2; }

# --- Helpers ---------------------------------------------------------------

env_get() {
  local env_file="$1"
  local key="$2"
  awk -F= -v k="$key" '
    $1 ~ "^[[:space:]]*"k"[[:space:]]*$" {
      v=$0; sub("^[^=]*=","",v);
      gsub(/^[[:space:]]+|[[:space:]]+$/,"",v);
      if (v ~ /^".*"$/) { sub(/^"/,"",v); sub(/"$/,"",v); }
      print v; exit
    }
  ' "${env_file}"
}

# --- Iterate over all stacks ----------------------------------------------

for STACK_NAME in "$@"; do
  echo
  log "============================================================"
  log "Purging stack: ${STACK_NAME}"
  log "============================================================"

  STACK_DIR="/opt/docker/${STACK_NAME}"
  ENV_FILE="${STACK_DIR}/.env/env"
  COMPOSE_FILE="${STACK_DIR}/docker-compose.yml"

  if [[ ! -d "${STACK_DIR}" ]]; then
    warn "Stack dir not found: ${STACK_DIR} (skipping)"
    continue
  fi

  # --- Detect DB backend (best effort) ------------------------------------

  DB_BACKEND=""
  DB_NAME="${STACK_NAME}"

  if [[ -f "${ENV_FILE}" ]]; then
    KC_DB="$(env_get "${ENV_FILE}" KC_DB 2>/dev/null || true)"
    KC_DB_URL="$(env_get "${ENV_FILE}" KC_DB_URL 2>/dev/null || true)"

    if [[ -n "${KC_DB}" ]]; then
      if echo "${KC_DB}" | grep -qi "postgres"; then
        DB_BACKEND="postgres"
      elif echo "${KC_DB}" | grep -qi "mariadb"; then
        DB_BACKEND="mariadb"
      fi
    fi

    if [[ -z "${DB_BACKEND}" && -n "${KC_DB_URL}" ]]; then
      if echo "${KC_DB_URL}" | grep -qi "postgresql"; then
        DB_BACKEND="postgres"
      elif echo "${KC_DB_URL}" | grep -qi "mariadb"; then
        DB_BACKEND="mariadb"
      fi

      if echo "${KC_DB_URL}" | grep -q "/"; then
        DB_NAME="$(echo "${KC_DB_URL}" | sed -E 's|.*\/([^/?#]+).*|\1|')"
      fi
    fi

    if [[ -z "${DB_BACKEND}" ]]; then
      if grep -qi "postgres" "${ENV_FILE}"; then
        DB_BACKEND="postgres"
      elif grep -qi "mariadb" "${ENV_FILE}"; then
        DB_BACKEND="mariadb"
      fi
    fi
  else
    warn "Env file not found: ${ENV_FILE} (DB detection skipped)"
  fi

  log "Stack dir:  ${STACK_DIR}"

  if [[ -n "${DB_BACKEND}" ]]; then
    log "DB backend: ${DB_BACKEND}"
    log "DB name:    ${DB_NAME}"
  else
    warn "No DB backend detected — skipping DB drop"
  fi

  # --- Drop database (optional) -------------------------------------------

  if [[ "${DB_BACKEND}" == "postgres" ]]; then
    log "Dropping Postgres database '${DB_NAME}'..."
    docker exec -i postgres psql -U postgres -v ON_ERROR_STOP=1 <<SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "${DB_NAME}";
SQL

  elif [[ "${DB_BACKEND}" == "mariadb" ]]; then
    MARIADB_ENV="/opt/docker/mariadb/.env/env"
    if [[ -f "${MARIADB_ENV}" ]]; then
      MARIADB_ROOT_PASSWORD="$(env_get "${MARIADB_ENV}" MARIADB_ROOT_PASSWORD || true)"
      if [[ -n "${MARIADB_ROOT_PASSWORD}" ]]; then
        log "Dropping MariaDB database '${DB_NAME}'..."
        docker exec -i mariadb mariadb -uroot -p"${MARIADB_ROOT_PASSWORD}" \
          -e "DROP DATABASE IF EXISTS \`${DB_NAME}\`;"
      else
        warn "MARIADB_ROOT_PASSWORD not found — skipping DB drop"
      fi
    else
      warn "MariaDB env file not found — skipping DB drop"
    fi
  fi

  # --- Stop/remove compose stack ------------------------------------------

  if [[ -f "${COMPOSE_FILE}" ]]; then
    log "Stopping/removing compose stack..."
    docker compose -f "${COMPOSE_FILE}" down --remove-orphans || true
  else
    warn "No docker-compose.yml found — skipping compose down"
  fi

  # --- Delete volumes + stack dir -----------------------------------------

  if [[ -d "${STACK_DIR}/volumes" ]]; then
    log "Removing local volumes dir: ${STACK_DIR}/volumes"
    rm -rf "${STACK_DIR}/volumes"
  else
    log "No local volumes dir found (ok)"
  fi

  log "Removing stack directory: ${STACK_DIR}"
  rm -rf "${STACK_DIR}"

  log "Stack '${STACK_NAME}' purged."
done

log "All requested stacks processed."
