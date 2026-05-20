#!/usr/bin/env bash
# Generic parallel-make wrapper. Takes one or more make targets as
# args, derives `-j` from min(arg-count, INFINITO_WORKER_CPU) so each
# target gets at most one CPU and never more workers than necessary,
# runs them with --output-sync=target to keep logs readable, and
# prints wall-clock elapsed time at the end.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

if [[ $# -eq 0 ]]; then
	echo "scripts/make/parallel.sh: at least one make target required" >&2 # nocheck: self-path-reference
	exit 2
fi

# shellcheck source=scripts/meta/env/load.sh
source scripts/meta/env/load.sh

: "${INFINITO_WORKER_CPU:?INFINITO_WORKER_CPU must be set (provided by env/static.env via the env loader)}"

n_targets=$#
if ((n_targets < INFINITO_WORKER_CPU)); then
	jobs="${n_targets}"
else
	jobs="${INFINITO_WORKER_CPU}"
fi

format_duration() {
	local seconds="$1"
	printf '%dm %02ds' "$((seconds / 60))" "$((seconds % 60))"
}

echo
echo "🚀  parallel make dispatch"
echo "    📋  targets:  $*"
echo "    ⚙️   jobs:     ${jobs}  (cpu cap: ${INFINITO_WORKER_CPU})"
echo

SECONDS=0
make -j "${jobs}" --output-sync=target "$@"
elapsed=$SECONDS

echo
echo "✨  done in $(format_duration "${elapsed}")  🎉"
echo
