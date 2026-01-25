#!/usr/bin/env bash
set -euo pipefail

: "${PYTHON:?PYTHON not set}"

EXTRA="${1:-}"

install_python_deps() {
  echo "📦 Installing Python dependencies"

  "${PYTHON}" -m pip install --upgrade pip setuptools wheel

  if [[ -n "${EXTRA}" ]]; then
    echo "→ Installing with extras: [${EXTRA}]"
    "${PYTHON}" -m pip install -e ".[${EXTRA}]"
  else
    echo "→ Installing base package"
    "${PYTHON}" -m pip install -e .
  fi
}

install_python_deps
