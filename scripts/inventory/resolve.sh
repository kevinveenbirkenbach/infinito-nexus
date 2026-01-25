#!/usr/bin/env bash
set -euo pipefail

# Resolve INVENTORY_DIR based on Makefile-provided environment.
#
# Required env (must be set by Makefile):
#   RUNNING_ON_ACT     : true|false
#   RUNNING_ON_GITHUB  : true|false
#
# Uses:
#   HOME
#
# Output:
#   Prints resolved INVENTORY_DIR to stdout (single line)
#   (no mkdir, no side-effects)

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "[FATAL] ${name} must be set by Makefile" >&2
    exit 2
  fi
}

normalize_bool() {
  local v="${1:-}"
  case "${v}" in
    true|false) printf '%s' "${v}" ;;
    *)
      echo "[FATAL] invalid boolean value: '${v}' (expected true|false)" >&2
      exit 2
      ;;
  esac
}

require_env "RUNNING_ON_ACT"
require_env "RUNNING_ON_GITHUB"
: "${HOME:?HOME must be set}"

RUNNING_ON_ACT="$(normalize_bool "${RUNNING_ON_ACT}")"
RUNNING_ON_GITHUB="$(normalize_bool "${RUNNING_ON_GITHUB}")"

if [[ "${RUNNING_ON_ACT}" == "true" ]]; then
  INVENTORY_DIR="${HOME}/inventories/act"
elif [[ "${RUNNING_ON_GITHUB}" == "true" ]]; then
  INVENTORY_DIR="${HOME}/inventories/github"
else
  INVENTORY_DIR="${HOME}/inventories/localhost"
fi

# IMPORTANT: single-line output for Makefile $(shell ...)
printf '%s\n' "${INVENTORY_DIR}"
