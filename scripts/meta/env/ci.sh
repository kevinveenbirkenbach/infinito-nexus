#!/usr/bin/env bash
# shellcheck shell=bash
#
# Mark the current shell as a make-driven deploy run so MODE_CI in
# group_vars/all/01_modes.yml flips to true (requirement 006).
#
# Sourced exclusively by the entry-point scripts under
# `scripts/tests/deploy/local/deploy/*.sh`. NOT sourced from
# `scripts/meta/env/all.sh`: the marker MUST surface only when a
# deploy command actually runs, never for unrelated `make test*` /
# `make build*` recipes that share the same BASH_ENV.

set -euo pipefail

if [[ "${INFINITO_ENV_CI_LOADED:-}" == "1" ]]; then
	return 0
fi
export INFINITO_ENV_CI_LOADED="1"

: "${INFINITO_MAKE_DEPLOY:=1}"
export INFINITO_MAKE_DEPLOY
