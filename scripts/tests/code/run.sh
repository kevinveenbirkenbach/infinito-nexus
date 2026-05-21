#!/usr/bin/env bash
# Runs the actual unittest discover invocation for the test suite picked
# by INFINITO_TEST_TYPE / INFINITO_TEST_PATTERN. Invoked either directly on the host or
# inside the infinito compose container by scripts/tests/code/wrapper.sh
# -- the body is identical for both runners.
set -euo pipefail

: "${INFINITO_TEST_PATTERN:?INFINITO_TEST_PATTERN must be set}"
: "${INFINITO_TEST_TYPE:?INFINITO_TEST_TYPE must be set}" # nocheck: makefile-supplied

NIX_CONFIG_EFFECTIVE="$(
	printf "%s\n%s\n" \
		"${NIX_CONFIG:-}" \
		"accept-flake-config = true" |
		sed -e "s/[[:space:]]\+$//" -e "/^$/d" |
		awk '!seen[$0]++'
)"
export NIX_CONFIG="${NIX_CONFIG_EFFECTIVE}"

echo "PWD=$(pwd)"
echo "PYTHON=${PYTHON:-<unset>}"

if [ -n "${PYTHON:-}" ]; then
	PATH="$(dirname "$PYTHON"):$PATH"
	export PATH
fi

make setup
"${PYTHON:-python3}" -m unittest discover -s "tests/${INFINITO_TEST_TYPE}" -t . -p "${INFINITO_TEST_PATTERN}" # nocheck: makefile-supplied
