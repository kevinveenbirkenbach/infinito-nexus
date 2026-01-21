#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# 🐍 Virtualenv bootstrap & setup
#
# This script is responsible for creating the Python virtualenv
# used by the entire Infinito.Nexus toolchain.
#
# Important design rule:
#   ❗ The venv Python interpreter CANNOT be used before the venv exists.
#   ❗ Therefore we must bootstrap using system python3 first.
#
# Lifecycle:
#   1) Use system python3 to create the venv
#   2) Afterwards, Makefile provides PYTHON=${VENV}/bin/python
#   3) All tooling runs inside the venv from then on
#
# This avoids chicken-and-egg failures in CI and on fresh machines.
# ------------------------------------------------------------

: "${VENV:?VENV not set (e.g. /opt/venvs/infinito)}"
: "${VENV_BASE:?VENV_BASE not set (e.g. /opt/venvs)}"

install_venv() {
  # 🛠 Bootstrap interpreter (system Python, outside of venv)
  # Used ONLY to CREATE the virtualenv.
  local bootstrap_python="python3"

  # 📦 Target interpreter inside the venv (may not exist yet!)
  local venv_python="${VENV}/bin/python"

  echo "🐍 Virtualenv target  : ${VENV}"
  echo "📁 Virtualenv base    : ${VENV_BASE}"
  echo "🛠 Bootstrap python   : ${bootstrap_python}"
  echo "🎯 Venv python target : ${venv_python}"
  echo

  # Ensure base directory exists (e.g. /opt/venvs)
  if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    mkdir -p "${VENV_BASE}"
  fi

  # ------------------------------------------------------------
  # Create venv if missing
  # ------------------------------------------------------------
  if [[ ! -x "${venv_python}" ]]; then
    echo "→ Creating virtualenv ${VENV}"
    "${bootstrap_python}" -m venv "${VENV}"
    echo "✅ Virtualenv created"
  else
    echo "→ Virtualenv already exists"
  fi
}

install_venv
