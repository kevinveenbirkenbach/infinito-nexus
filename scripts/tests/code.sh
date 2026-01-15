#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo ">>> Running UNIT tests in ${INFINITO_DISTRO} container"
echo "============================================================"

: "${INFINITO_DISTRO:?INFINITO_DISTRO must be set}"

# Prevent interactive Nix prompt for flake-provided nixConfig
# while still honoring any existing NIX_CONFIG from CI / env.
NIX_CONFIG_EFFECTIVE="$(
  printf "%s\n%s\n" \
    "${NIX_CONFIG:-}" \
    "accept-flake-config = true" \
  | sed -e 's/[[:space:]]\+$//' -e '/^$/d'
)"

INFINITO_DISTRO="${INFINITO_DISTRO}" docker compose --profile ci run --rm -T \
  -v "$(pwd):/opt/src/infinito" \
  -e INFINITO_COMPILE=1 \
  -e TEST_PATTERN="${TEST_PATTERN}" \
  -e TEST_TYPE="${TEST_TYPE}" \
  -e NIX_CONFIG="${NIX_CONFIG_EFFECTIVE}" \
  infinito \
  bash -lc '
    set -euo pipefail
    cd /opt/src/infinito

    echo "PWD=$(pwd)"
    echo "PYTHON=${PYTHON}"
    export PATH="$(dirname "$PYTHON"):$PATH"
    # Ensure we really use the exported interpreter (and thus the global venv)
    make setup
    "${PYTHON}" -m unittest discover -s tests/${TEST_TYPE} -t . -p "${TEST_PATTERN}"
  '
