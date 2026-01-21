#!/usr/bin/env bash
set -euo pipefail

: "${VENV:?VENV not set}"
: "${VENV_BASE:?VENV_BASE not set}"
: "${PYTHON:?PYTHON not set}"

install_venv() {
  echo "🐍 Using venv: ${VENV}"

  if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    mkdir -p "${VENV_BASE}"
  fi

  if [[ ! -x "${PYTHON}" ]]; then
    echo "→ Creating virtualenv ${VENV}"
    "${PYTHON}" -m venv "${VENV}"
  else
    echo "→ Virtualenv already exists"
  fi
}

install_venv
