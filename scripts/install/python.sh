#!/usr/bin/env bash
set -euo pipefail

: "${PYTHON:?PYTHON not set}"

EXTRA="${1:-}"

retry() {
  local attempts=7
  local delay=20
  local count=1

  while true; do
    if "$@"; then
      return 0
    fi

    if [[ $count -ge $attempts ]]; then
      echo "❌ Command failed after ${attempts} attempts."
      return 1
    fi

    echo "⚠️  Attempt ${count}/${attempts} failed. Retrying in ${delay}s..."
    sleep "${delay}"
    ((count++))
  done
}

install_python_deps() {
  echo "📦 Installing Python dependencies"

  retry "${PYTHON}" -m pip install --upgrade pip setuptools wheel

  if [[ -n "${EXTRA}" ]]; then
    echo "→ Installing with extras: [${EXTRA}]"
    retry "${PYTHON}" -m pip install -e ".[${EXTRA}]"
  else
    echo "→ Installing base package"
    retry "${PYTHON}" -m pip install -e .
  fi
}

install_python_deps
