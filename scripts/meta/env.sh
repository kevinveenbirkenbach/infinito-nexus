#!/usr/bin/env bash
# shellcheck shell=bash
#
# scripts/meta/env.sh
#
# This file is meant to be sourced automatically (e.g. via BASH_ENV from Makefile)
# or manually:
#   source scripts/meta/env.sh
#
# It defines and exports Infinito runtime env vars with sensible defaults.
# It is safe to run under: set -euo pipefail (including `-u`).

set -euo pipefail

# Prevent double-loading
if [[ "${INFINITO_ENV_LOADED:-}" == "1" ]]; then
  return 0
fi
export INFINITO_ENV_LOADED="1"

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
_is_true() { [[ "${1:-}" == "1" || "${1:-}" == "true" ]]; }

# ------------------------------------------------------------
# Venv / Python (safe under "set -u")
# ------------------------------------------------------------
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

# Ensure repo root is importable (so module_utils/, filter_plugins/ etc. work)
: "${PYTHONPATH:=.}"
export PYTHONPATH

# ------------------------------------------------------------
# CI detection
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# Defaults
# ------------------------------------------------------------
: "${TEST_DEPLOY_TYPE:=server}"
export TEST_DEPLOY_TYPE

: "${TEST_PATTERN:=test*.py}"
export TEST_PATTERN

: "${INFINITO_DISTRO:=debian}"
: "${INFINITO_CONTAINER:=infinito_nexus_${INFINITO_DISTRO}}"
export INFINITO_DISTRO INFINITO_CONTAINER

# Common distro list (used by build-no-cache-all)
: "${DISTROS:=arch debian ubuntu fedora centos}"
export DISTROS

# ------------------------------------------------------------
# Inventory dir (needs resolve script)
# ------------------------------------------------------------
if [[ -z "${INVENTORY_DIR:-}" ]]; then
  INVENTORY_DIR="$(
    RUNNING_ON_ACT="${RUNNING_ON_ACT}" \
    RUNNING_ON_GITHUB="${RUNNING_ON_GITHUB}" \
    HOME="${HOME:-}" \
    bash scripts/inventory/resolve.sh
  )"
fi
export INVENTORY_DIR

# ------------------------------------------------------------
# GitHub CI overrides
# ------------------------------------------------------------
if [[ "${RUNNING_ON_GITHUB}" == "true" ]]; then
  : "${INFINITO_PULL_POLICY:=always}"
  : "${INFINITO_IMAGE_TAG:=latest}"

  # Owner can come from GitHub Actions or be provided explicitly (fallback).
  _owner="${GITHUB_REPOSITORY_OWNER:-${OWNER:-}}"
  : "${INFINITO_IMAGE:=ghcr.io/${_owner}/infinito-${INFINITO_DISTRO}:${INFINITO_IMAGE_TAG}}"

  : "${INFINITO_NO_BUILD:=1}"
  : "${INFINITO_DOCKER_VOLUME:=/mnt/docker}"
  : "${INFINITO_DOCKER_MOUNT:=/var/lib/docker}"
  : "${INFINITO_COMPILE:=0}"

  export INFINITO_PULL_POLICY INFINITO_IMAGE_TAG INFINITO_IMAGE INFINITO_NO_BUILD
  export INFINITO_DOCKER_VOLUME INFINITO_DOCKER_MOUNT
  export INFINITO_COMPILE
else
  : "${INFINITO_COMPILE:=1}"
  export INFINITO_COMPILE
fi

# NIX_CONFIG is optional; export if set
if [[ -n "${NIX_CONFIG:-}" ]]; then
  export NIX_CONFIG
fi
