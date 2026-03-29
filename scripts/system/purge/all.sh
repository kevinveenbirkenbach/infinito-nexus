#!/usr/bin/env bash
set -euo pipefail

usage() {
	cat <<'EOF'
Usage:
  all.sh [--help]

Runs the broader cleanup bundle:
  1. build-cleanup
  2. purge-system

Each step is best-effort. The script exits non-zero if any step fails.
EOF
}

case "${1:-}" in
-h | --help)
	usage
	exit 0
	;;
esac

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

cd "${REPO_ROOT}"

log() {
	echo ">>> $*"
}

warn() {
	echo "!!! WARNING: $*" >&2
}

run_make_target() {
	local target="$1"

	log "Running ${target}"

	if make "${target}"; then
		return 0
	else
		local rc=$?
		warn "${target} failed (rc=${rc})"
		return "${rc}"
	fi
}

overall_rc=0

for target in build-cleanup purge-system; do
	if ! run_make_target "${target}"; then
		overall_rc=1
	fi
done

exit "${overall_rc}"
