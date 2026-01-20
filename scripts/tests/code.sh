#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo ">>> Running UNIT tests                                      "
echo "============================================================"

: "${TEST_PATTERN:?TEST_PATTERN must be set}"
: "${TEST_TYPE:?TEST_TYPE must be set}"

set -euo pipefail

# Keep old NIX flake behavior
NIX_CONFIG_EFFECTIVE="$(
  printf '%s\n%s\n' \
    "${NIX_CONFIG:-}" \
    'accept-flake-config = true' \
  | sed -e 's/[[:space:]]\+$//' -e '/^$/d'
)"
export NIX_CONFIG="${NIX_CONFIG_EFFECTIVE}"

echo "PWD=$(pwd)"
echo "PYTHON=${PYTHON}"

export PATH="$(dirname "$PYTHON"):$PATH"

make setup
"$PYTHON" -m unittest discover -s tests/${TEST_TYPE} -t . -p "${TEST_PATTERN}"
