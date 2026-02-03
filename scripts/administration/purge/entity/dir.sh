#!/usr/bin/env bash
# Removes stack directory and its volumes dir:
#   /opt/docker/<STACK>/volumes
#   /opt/docker/<STACK>
#
# Usage:
#   ./purge/entity/dir.sh <STACK1> [STACK2] [...]

set -euo pipefail

if [[ "$#" -lt 1 ]]; then
  echo "ERROR: No stack names provided." >&2
  exit 2
fi

log()  { echo ">>> $*"; }
warn() { echo "!!! WARNING: $*" >&2; }

overall_rc=0

for STACK_NAME in "$@"; do
(
  set -euo pipefail

  STACK_DIR="/opt/docker/${STACK_NAME}"

  if [[ ! -d "${STACK_DIR}" ]]; then
    warn "Stack dir not found for '${STACK_NAME}' (${STACK_DIR}) — skipping filesystem cleanup"
    exit 0
  fi

  if [[ -d "${STACK_DIR}/volumes" ]]; then
    log "Removing volumes dir for '${STACK_NAME}'"
    rm -rf "${STACK_DIR}/volumes"
  fi

  log "Removing stack directory for '${STACK_NAME}'"
  rm -rf "${STACK_DIR}"
) || {
  rc=$?
  overall_rc=1
  warn "Filesystem cleanup failed for '${STACK_NAME}' (rc=${rc}) — continuing"
}
done

exit "${overall_rc}"
