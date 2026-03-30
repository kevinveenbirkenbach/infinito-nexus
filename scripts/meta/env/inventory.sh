#!/usr/bin/env bash
# shellcheck shell=bash
#
# Resolve inventory path.

set -euo pipefail

if [[ "${INFINITO_ENV_INVENTORY_LOADED:-}" == "1" ]]; then
	return 0
fi
export INFINITO_ENV_INVENTORY_LOADED="1"

: "${RUNNING_ON_ACT:=false}"
: "${RUNNING_ON_GITHUB:=false}"

if [[ -z "${INVENTORY_DIR:-}" ]]; then
	INVENTORY_DIR="$(
		RUNNING_ON_ACT="${RUNNING_ON_ACT}" \
			RUNNING_ON_GITHUB="${RUNNING_ON_GITHUB}" \
			HOME="${HOME:-}" \
			bash scripts/inventory/resolve.sh
	)"
fi
export INVENTORY_DIR

# SPOT: canonical path to the generated inventory devices file.
INVENTORY_FILE="${INVENTORY_DIR}/devices.yml"
export INVENTORY_FILE

# SPOT: canonical path to the host_vars file for localhost.
HOST_VARS_FILE="${INVENTORY_DIR}/host_vars/localhost.yml"
export HOST_VARS_FILE
