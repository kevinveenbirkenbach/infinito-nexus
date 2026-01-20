#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo ">>> Running UNIT tests in ${INFINITO_DISTRO:-<unset>} container (compose stack)"
echo "============================================================"

: "${INFINITO_DISTRO:?INFINITO_DISTRO must be set}"
: "${TEST_PATTERN:?TEST_PATTERN must be set}"
: "${TEST_TYPE:?TEST_TYPE must be set}"

# 1) Bring up the development compose stack (coredns + infinito).
#    This uses the new Python orchestrator (healthcheck + entry init).
python3 -m cli.deploy.development up \
  --no-build \
  --distro "${INFINITO_DISTRO}"

# 2) Run tests inside the already running infinito container via the new exec wrapper.
#    We keep the old NIX_CONFIG behavior (flake config acceptance) but run it inside the container.
python3 -m cli.deploy.development exec \
  --distro "${INFINITO_DISTRO}" -- \
  bash -lc "
    set -euo pipefail

    NIX_CONFIG_EFFECTIVE=\"\$(
      printf '%s\n%s\n' \
        \"\${NIX_CONFIG:-}\" \
        'accept-flake-config = true' \
      | sed -e 's/[[:space:]]\\+$//' -e '/^$/d'
    )\"
    export NIX_CONFIG=\"\${NIX_CONFIG_EFFECTIVE}\"

    cd /opt/src/infinito

    echo \"PWD=\$(pwd)\"
    echo \"PYTHON=\${PYTHON}\"

    export PATH=\"\$(dirname \"\$PYTHON\"):\$PATH\"
    make setup
    \"\$PYTHON\" -m unittest discover -s tests/${TEST_TYPE} -t . -p \"${TEST_PATTERN}\"
  "
