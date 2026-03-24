#!/usr/bin/env bash
# shellcheck shell=bash
#
# Resolve project default values.

set -euo pipefail

if [[ "${INFINITO_ENV_DEFAULTS_LOADED:-}" == "1" ]]; then
	return 0
fi
export INFINITO_ENV_DEFAULTS_LOADED="1"

: "${TEST_DEPLOY_TYPE:=server}"
export TEST_DEPLOY_TYPE

: "${TEST_PATTERN:=test*.py}"
export TEST_PATTERN

: "${INFINITO_DISTRO:=debian}"
: "${INFINITO_CONTAINER:=infinito_nexus_${INFINITO_DISTRO}}"
export INFINITO_DISTRO INFINITO_CONTAINER

: "${DISTROS:=arch debian ubuntu fedora centos}"
export DISTROS
