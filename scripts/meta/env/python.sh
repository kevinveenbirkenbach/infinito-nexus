#!/usr/bin/env bash
# shellcheck shell=bash
#
# Resolve Python/venv-related environment variables.

set -euo pipefail

if [[ "${INFINITO_ENV_PYTHON_LOADED:-}" == "1" ]]; then
	return 0
fi
export INFINITO_ENV_PYTHON_LOADED="1"

_virtual_env="${VIRTUAL_ENV:-}"
if [[ -n "${_virtual_env}" ]]; then
	: "${VENV_BASE:=${VENV_BASE:-$(dirname "${_virtual_env}")/}}"
else
	: "${VENV_BASE:=${VENV_BASE:-/opt/venvs}}"
fi

: "${VENV_NAME:=infinito}"
: "${VENV_FALLBACK:=${VENV_BASE%/}/${VENV_NAME}}"
: "${VENV:=${_virtual_env:-$VENV_FALLBACK}}"

_default_python="${VENV%/}/bin/python"
if [[ -x "${_default_python}" ]]; then
	: "${PYTHON:=${_default_python}}"
else
	: "${PYTHON:=python3}"
fi

: "${PIP:=${PYTHON} -m pip}"

export VENV_BASE VENV_NAME VENV_FALLBACK VENV
export PYTHON PIP

_venv_bin="${VENV%/}/bin"
if [[ -d "${_venv_bin}" ]]; then
	case ":${PATH:-}:" in
	*:"${_venv_bin}":*) ;;
	*)
		export PATH="${_venv_bin}${PATH:+:${PATH}}"
		;;
	esac
fi

: "${PYTHONPATH:=.}"
export PYTHONPATH
