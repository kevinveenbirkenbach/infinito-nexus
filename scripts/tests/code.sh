#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo ">>> Running UNIT tests in ${INFINITO_DISTRO:-<unset>} container (compose stack)"
echo "============================================================"

: "${INFINITO_DISTRO:?INFINITO_DISTRO must be set}"
: "${TEST_PATTERN:?TEST_PATTERN must be set}"
: "${TEST_TYPE:?TEST_TYPE must be set}"

# Execute directly inside the already running infinito container
INFINITO_DISTRO="${INFINITO_DISTRO}" \
docker compose --profile ci exec -T \
  -e TEST_PATTERN="${TEST_PATTERN}" \
  -e TEST_TYPE="${TEST_TYPE}" \
  --workdir /opt/src/infinito \
  infinito \
  bash -lc '
    set -euo pipefail

    NIX_CONFIG_EFFECTIVE="$(
      printf "%s\n%s\n" \
        "${NIX_CONFIG:-}" \
        "accept-flake-config = true" \
      | sed -e "s/[[:space:]]\+$//" -e "/^$/d"
    )"
    export NIX_CONFIG="${NIX_CONFIG_EFFECTIVE}"

    echo "PWD=$(pwd)"
    echo "PYTHON=${PYTHON:-<unset>}"

    if [ -n "${PYTHON:-}" ]; then
      export PATH="$(dirname "$PYTHON"):$PATH"
    fi

    make setup
    "${PYTHON}" -m unittest discover -s "tests/${TEST_TYPE}" -t . -p "${TEST_PATTERN}"
  '
