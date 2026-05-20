#!/usr/bin/env bash
# shellcheck shell=bash
#
# Project env loader -- the single entry point that pulls the generated
# `.env` file into the current shell. `.env` is produced by
# `python -m cli.meta.env` (a.k.a. `make dotenv`) from the committed
# `env/default.env` plus runtime context (distro, GHA/Act flags,
# df/meminfo-derived sizes, sha256 secrets, etc.). `.env` is the single
# source of truth for both static defaults and runtime-resolved values.
#
# Behaviour:
#   * Idempotent via INFINITO_ENV_LOADED guard.
#   * Auto-generates `.env` on first source if it is missing, so a cold
#     sourcing this loader works even before `make dotenv` has run. # nocheck: self-path-reference
#   * Exports every variable declared in `.env`, BUT respects values
#     that are already set in the caller's environment (setdefault
#     semantics): `FOO=bar make ...` keeps `FOO=bar` even when `.env`
#     declares its own default for `FOO`.
#   * Prepends ${VENV}/bin to PATH when the venv exists (mirrors the
#     legacy python.sh side-effect; not exported into `.env` because
#     mutating PATH via a static snapshot is brittle).
#
# Re-entrancy guard:
#   The Makefile exports BASH_ENV=$(ENV_SH), so every bash subprocess --
#   including those spawned by `python -m cli.meta.env` itself (which
#   shells out to e.g. scripts/inventory/resolve.sh) -- would otherwise
#   re-enter this script. While generating, `.env` is still missing,
#   and the generator would be called recursively until OOM. We set
#   INFINITO_ENV_GENERATING=1 around the generator invocation and
#   short-circuit here when we see it, so subprocesses skip the load
#   entirely during generation.

if [[ "${INFINITO_ENV_LOADED:-}" == "1" ]]; then
	return 0
fi
if [[ "${INFINITO_ENV_GENERATING:-}" == "1" ]]; then
	return 0
fi

_infinito_env_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
_infinito_env_dotenv="${_infinito_env_repo_root}/.env"

if [[ ! -f "${_infinito_env_dotenv}" ]]; then
	(
		cd "${_infinito_env_repo_root}" || exit 1
		export INFINITO_ENV_GENERATING=1
		python3 -m cli.meta.env
	) >&2
fi

# Snapshot any pre-existing non-empty values for keys declared in
# `.env` so we can restore them after the bulk `source`. This gives us
# setdefault semantics: caller-set values win over the static default
# in `.env`.
declare -A _infinito_env_preserved=()
while IFS= read -r _infinito_env_line; do
	case "${_infinito_env_line}" in
	"" | "#"*) continue ;;
	esac
	_infinito_env_key="${_infinito_env_line%%=*}"
	if [[ "${_infinito_env_key}" == "${_infinito_env_line}" ]]; then
		continue
	fi
	if [[ -n "${!_infinito_env_key:-}" ]]; then
		_infinito_env_preserved["${_infinito_env_key}"]="${!_infinito_env_key}"
	fi
done <"${_infinito_env_dotenv}"
unset _infinito_env_line _infinito_env_key

set -a
# shellcheck disable=SC1090
source "${_infinito_env_dotenv}"
set +a

for _infinito_env_key in "${!_infinito_env_preserved[@]}"; do
	declare -gx "${_infinito_env_key}=${_infinito_env_preserved[${_infinito_env_key}]}"
done
unset _infinito_env_key _infinito_env_preserved

if [[ -n "${VENV:-}" ]]; then
	_infinito_venv_bin="${VENV%/}/bin"
	if [[ -d "${_infinito_venv_bin}" ]]; then
		case ":${PATH:-}:" in
		*:"${_infinito_venv_bin}":*) ;;
		*)
			export PATH="${_infinito_venv_bin}${PATH:+:${PATH}}"
			;;
		esac
	fi
	unset _infinito_venv_bin
fi

export INFINITO_ENV_LOADED="1"
unset _infinito_env_repo_root _infinito_env_dotenv
