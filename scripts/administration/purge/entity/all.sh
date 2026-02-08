#!/usr/bin/env bash
# Orchestrates entity purge:
#   1) DB purge (drop or truncate)
#   2) docker compose down -v
#   3) remove /opt/compose/<STACK>/volumes and /opt/compose/<STACK>
#
# Usage:
#   ./purge/entity/all.sh [--wipe-data-only] [--db-only] <STACK1> [STACK2] [...]
#
# Flags:
#   --wipe-data-only  Truncate all tables (keep schema) instead of dropping the DB
#   --db-only         Only perform DB purge; skip compose and filesystem cleanup

set -euo pipefail

WIPE_DATA_ONLY=false
DB_ONLY=false

while [[ "${1:-}" == --* ]]; do
  case "${1}" in
    --wipe-data-only) WIPE_DATA_ONLY=true; shift ;;
    --db-only)        DB_ONLY=true; shift ;;
    --help|-h)
      cat <<'EOF'
Usage:
  purge/entity/all.sh [--wipe-data-only] [--db-only] <STACK1> [STACK2] [...]

Flags:
  --wipe-data-only  Truncate all tables (keep schema) instead of dropping DB
  --db-only         Only purge DB; skip compose down and filesystem cleanup
EOF
      exit 0
      ;;
    *)
      echo "ERROR: Unknown flag: ${1}" >&2
      exit 2
      ;;
  esac
done

if [[ "$#" -lt 1 ]]; then
  echo "ERROR: No stack names provided." >&2
  echo "Usage: $0 [--wipe-data-only] [--db-only] <STACK1> [STACK2] [...]" >&2
  exit 2
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

log()  { echo ">>> $*"; }
warn() { echo "!!! WARNING: $*" >&2; }

overall_rc=0

for STACK_NAME in "$@"; do
(
  set -euo pipefail

  echo
  log "============================================================"
  log "Purging stack: ${STACK_NAME}"
  log "============================================================"

  db_args=()
  if [[ "${WIPE_DATA_ONLY}" == "true" ]]; then
    db_args+=(--wipe-data-only)
  fi

  # 1) DB purge always (requested: try both backends best effort)
  "${SCRIPT_DIR}/db.sh" "${db_args[@]}" "${STACK_NAME}"

  # 2/3) Optional: compose + filesystem cleanup
  if [[ "${DB_ONLY}" == "true" ]]; then
    log "DB-only mode active — skipping compose and filesystem cleanup"
    exit 0
  fi

  "${SCRIPT_DIR}/compose.sh" "${STACK_NAME}"
  "${SCRIPT_DIR}/dir.sh" "${STACK_NAME}"

  log "Stack '${STACK_NAME}' purged."
) || {
  rc=$?
  overall_rc=1
  warn "Stack '${STACK_NAME}' purge failed (rc=${rc}) — continuing"
}
done

log "All requested stacks processed."
exit "${overall_rc}"
