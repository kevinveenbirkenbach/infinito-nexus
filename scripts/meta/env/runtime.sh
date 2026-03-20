#!/usr/bin/env bash
# shellcheck shell=bash
#
# Resolve runtime context flags (local, act, github).

set -euo pipefail

if [[ "${INFINITO_ENV_RUNTIME_LOADED:-}" == "1" ]]; then
	return 0
fi
export INFINITO_ENV_RUNTIME_LOADED="1"

: "${RUNNING_ON_ACT:=false}"
: "${RUNNING_ON_GITHUB:=false}"

if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
	RUNNING_ON_GITHUB="true"
	if [[ "${ACT:-}" == "true" ]]; then
		RUNNING_ON_ACT="true"
		RUNNING_ON_GITHUB="false"
	fi
fi

export RUNNING_ON_ACT RUNNING_ON_GITHUB
