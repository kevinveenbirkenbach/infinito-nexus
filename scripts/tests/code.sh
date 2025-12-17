#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo ">>> Running UNIT tests in ${INFINITO_DISTRO} container"
echo "============================================================"

docker run --rm \
  -e REINSTALL_INFINITO=1 \
  -e PYTHON="${PYTHON}" \
  -e TEST_PATTERN="${TEST_PATTERN}" \
  -e TEST_TYPE="${TEST_TYPE}" \
  -v "$(pwd):/opt/src/infinito" \
  "infinito-${INFINITO_DISTRO}" \
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
