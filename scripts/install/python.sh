#!/usr/bin/env bash
set -euo pipefail

: "${PYTHON:?PYTHON not set}"

install_python_deps() {
  echo "📦 Installing Python dependencies"

  "${PYTHON}" -m pip install --upgrade pip setuptools wheel
  "${PYTHON}" -m pip install -e .
}

install_python_deps
