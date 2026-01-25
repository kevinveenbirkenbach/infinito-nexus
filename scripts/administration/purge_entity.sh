#!/usr/bin/env bash
# purge_entity.sh
#
# Usage:
#   ./purge_entity.sh [--wipe-data-only] <STACK1> [STACK2] [...]
#
# Examples:
#   ./purge_entity.sh keycloak openldap nextcloud
#   ./purge_entity.sh --wipe-data-only keycloak nextcloud
#
# What it does per stack:
#   - Detects DB backend (postgres/mariadb) best effort
#   - Without --wipe-data-only:
#       * DROP DATABASE IF EXISTS
#   - With --wipe-data-only:
#       * TRUNCATE ALL TABLES (structure preserved)
#   - docker compose down -v
#   - removes /opt/docker/<STACK>/volumes
#   - removes /opt/docker/<STACK>

set -euo pipefail

# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------

WIPE_DATA_ONLY=false

if [[ "${1:-}" == "--wipe-data-only" ]]; then
  WIPE_DATA_ONLY=true
  shift
fi

if [[ "$#" -lt 1 ]]; then
  echo "ERROR: No stack names provided."
  echo "Usage: $0 [--wipe-data-only] <STACK1> [STACK2] [...]"
  exit 2
fi

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

log()  { echo ">>> $*"; }
warn() { echo "!!! WARNING: $*" >&2; }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

env_get() {
  local env_file="$1"
  local key="$2"

  awk -F= -v k="$key" '
    $1 ~ "^[[:space:]]*"k"[[:space:]]*$" {
      v=$0
      sub("^[^=]*=","",v)
      gsub(/^[[:space:]]+|[[:space:]]+$/,"",v)
      if (v ~ /^".*"$/) { sub(/^"/,"",v); sub(/"$/,"",v) }
      print v
      exit
    }
  ' "${env_file}"
}

# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------

drop_postgres_db_best_effort() {
  local db_name="$1"

  local admin_db="postgres"
  [[ "${db_name}" == "postgres" ]] && admin_db="template1"

  log "Dropping Postgres database '${db_name}' (admin db: ${admin_db})..."

  set +e
  docker exec -i postgres psql -U postgres -d "${admin_db}" <<SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '${db_name}' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "${db_name}";
SQL
  local rc=$?
  set -e

  [[ $rc -ne 0 ]] && warn "Postgres DROP DATABASE failed for '${db_name}' (rc=${rc})"
}

truncate_postgres_db_best_effort() {
  local db_name="$1"

  log "Truncating all tables in Postgres database '${db_name}'..."

  set +e
  docker exec -i postgres psql -U postgres -d "${db_name}" <<'SQL'
DO $$
DECLARE
  r RECORD;
BEGIN
  FOR r IN
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'public'
  LOOP
    EXECUTE 'TRUNCATE TABLE public.' || quote_ident(r.tablename) || ' CASCADE';
  END LOOP;
END $$;
SQL
  local rc=$?
  set -e

  [[ $rc -ne 0 ]] && warn "Postgres TRUNCATE failed for '${db_name}' (rc=${rc})"
}

# ---------------------------------------------------------------------------
# MariaDB
# ---------------------------------------------------------------------------

drop_mariadb_db_best_effort() {
  local db_name="$1"

  case "${db_name}" in
    mysql|information_schema|performance_schema|sys)
      warn "Refusing to drop MariaDB system database '${db_name}'"
      return 0
      ;;
  esac

  local mariadb_env="/opt/docker/mariadb/.env/env"
  [[ ! -f "${mariadb_env}" ]] && {
    warn "MariaDB env file not found — skipping DB drop"
    return 0
  }

  local root_pw
  root_pw="$(env_get "${mariadb_env}" MARIADB_ROOT_PASSWORD || true)"
  [[ -z "${root_pw}" ]] && {
    warn "MARIADB_ROOT_PASSWORD not found — skipping DB drop"
    return 0
  }

  log "Dropping MariaDB database '${db_name}'..."

  set +e
  docker exec -i mariadb mariadb -uroot -p"${root_pw}" \
    -e "DROP DATABASE IF EXISTS \`${db_name}\`;"
  local rc=$?
  set -e

  [[ $rc -ne 0 ]] && warn "MariaDB DROP DATABASE failed for '${db_name}' (rc=${rc})"
}

truncate_mariadb_db_best_effort() {
  local db_name="$1"

  local mariadb_env="/opt/docker/mariadb/.env/env"
  [[ ! -f "${mariadb_env}" ]] && {
    warn "MariaDB env file not found — skipping truncate"
    return 0
  }

  local root_pw
  root_pw="$(env_get "${mariadb_env}" MARIADB_ROOT_PASSWORD || true)"
  [[ -z "${root_pw}" ]] && {
    warn "MARIADB_ROOT_PASSWORD not found — skipping truncate"
    return 0
  }

  log "Truncating all tables in MariaDB database '${db_name}'..."

  set +e
  {
    echo "SET FOREIGN_KEY_CHECKS=0;"
    docker exec -i mariadb mariadb -uroot -p"${root_pw}" -N -B "${db_name}" <<'SQL'
SELECT CONCAT('TRUNCATE TABLE `', table_name, '`;')
FROM information_schema.tables
WHERE table_schema = DATABASE();
SQL
    echo "SET FOREIGN_KEY_CHECKS=1;"
  } | docker exec -i mariadb mariadb -uroot -p"${root_pw}" "${db_name}"
  local rc=$?
  set -e

  [[ $rc -ne 0 ]] && warn "MariaDB TRUNCATE failed for '${db_name}' (rc=${rc})"
}

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

for STACK_NAME in "$@"; do
  echo
  log "============================================================"
  log "Purging stack: ${STACK_NAME}"
  log "============================================================"

  STACK_DIR="/opt/docker/${STACK_NAME}"
  ENV_FILE="${STACK_DIR}/.env/env"
  COMPOSE_FILE="${STACK_DIR}/docker-compose.yml"

  [[ ! -d "${STACK_DIR}" ]] && {
    warn "Stack dir not found: ${STACK_DIR} — skipping"
    continue
  }

  DB_BACKEND=""
  DB_NAME="${STACK_NAME}"

  if [[ -f "${ENV_FILE}" ]]; then
    KC_DB="$(env_get "${ENV_FILE}" KC_DB || true)"
    KC_DB_URL="$(env_get "${ENV_FILE}" KC_DB_URL || true)"

    if [[ -n "${KC_DB}" ]]; then
      echo "${KC_DB}" | grep -qi postgres && DB_BACKEND="postgres" || true
      echo "${KC_DB}" | grep -qi mariadb  && DB_BACKEND="mariadb"  || true
    fi

    if [[ -z "${DB_BACKEND}" && -n "${KC_DB_URL}" ]]; then
      echo "${KC_DB_URL}" | grep -qi postgresql && DB_BACKEND="postgres" || true
      echo "${KC_DB_URL}" | grep -qi mariadb   && DB_BACKEND="mariadb"  || true
      DB_NAME="$(echo "${KC_DB_URL}" | sed -E 's|.*/([^/?#]+).*|\1|')"
    fi

    if [[ -z "${DB_BACKEND}" ]]; then
      grep -qi postgres "${ENV_FILE}" && DB_BACKEND="postgres" || true
    fi
    if [[ -z "${DB_BACKEND}" ]]; then
      grep -qi mariadb "${ENV_FILE}" && DB_BACKEND="mariadb" || true
    fi
  else
    warn "Env file not found — DB detection skipped"
  fi

  log "Stack dir: ${STACK_DIR}"
  if [[ -n "${DB_BACKEND}" ]]; then
    log "DB backend: ${DB_BACKEND} | DB name: ${DB_NAME}"
  else
    warn "No DB backend detected"
  fi


  if [[ "${DB_BACKEND}" == "postgres" ]]; then
    if [[ "${WIPE_DATA_ONLY}" == "true" ]]; then
      truncate_postgres_db_best_effort "${DB_NAME}"
    else
      drop_postgres_db_best_effort "${DB_NAME}"
    fi
  elif [[ "${DB_BACKEND}" == "mariadb" ]]; then
    if [[ "${WIPE_DATA_ONLY}" == "true" ]]; then
      truncate_mariadb_db_best_effort "${DB_NAME}"
    else
      drop_mariadb_db_best_effort "${DB_NAME}"
    fi
  fi

  if [[ -f "${COMPOSE_FILE}" ]]; then
    log "Stopping/removing compose stack..."
    docker compose -f "${COMPOSE_FILE}" down --remove-orphans -v || true
  else
    warn "docker-compose.yml not found — skipping compose down"
  fi

  [[ -d "${STACK_DIR}/volumes" ]] && {
    log "Removing volumes dir"
    rm -rf "${STACK_DIR}/volumes"
  }

  log "Removing stack directory"
  rm -rf "${STACK_DIR}"

  log "Stack '${STACK_NAME}' purged."
done

log "All requested stacks processed."
