#!/usr/bin/env bash
set -euo pipefail

# Open an interactive shell in the running infinito container, or execute a
# one-off command inside it when INSPECT_CMD or positional arguments are set.
#
# Usage:
#   scripts/tests/deploy/local/exec/container.sh
#   scripts/tests/deploy/local/exec/container.sh [command...]
#
# Environment:
#   INFINITO_DISTRO     arch|debian|ubuntu|fedora|centos
#   INFINITO_CONTAINER  Optional explicit container name
#   INSPECT_CMD         One-off shell command to run instead of an interactive shell
#
# Examples:
#   scripts/tests/deploy/local/exec/container.sh
#   scripts/tests/deploy/local/exec/container.sh whoami
#   INSPECT_CMD='whoami && id' scripts/tests/deploy/local/exec/container.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../../" && pwd)"

usage() {
	cat <<'EOF'
Usage:
  scripts/tests/deploy/local/exec/container.sh
  scripts/tests/deploy/local/exec/container.sh [command...]

Environment:
  INFINITO_DISTRO     arch|debian|ubuntu|fedora|centos
  INFINITO_CONTAINER  Optional explicit container name
  INSPECT_CMD         One-off shell command to run instead of an interactive shell

Examples:
  scripts/tests/deploy/local/exec/container.sh
  scripts/tests/deploy/local/exec/container.sh whoami
  INSPECT_CMD='whoami && id' scripts/tests/deploy/local/exec/container.sh
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
	usage
	exit 0
fi

cd "${REPO_ROOT}"

if [[ -f "scripts/meta/env/all.sh" ]]; then
	# shellcheck source=scripts/meta/env/all.sh
	source "scripts/meta/env/all.sh"
else
	echo "ERROR: missing scripts/meta/env/all.sh" >&2
	exit 2
fi

: "${INFINITO_DISTRO:=debian}"
: "${INFINITO_CONTAINER:=infinito_nexus_${INFINITO_DISTRO}}"

container="${INFINITO_CONTAINER}"

docker_exec_flags=(-i)
if [[ -t 0 && -t 1 ]]; then
	docker_exec_flags=(-it)
fi

if [[ $# -gt 0 ]]; then
	if [[ "${1:-}" == "--" ]]; then
		shift
	fi
	if [[ $# -eq 0 ]]; then
		usage
		exit 2
	fi
	exec docker exec "${docker_exec_flags[@]}" -w /opt/src/infinito "${container}" "$@"
fi

if [[ -n "${INSPECT_CMD:-}" ]]; then
	exec docker exec "${docker_exec_flags[@]}" -w /opt/src/infinito "${container}" sh -lc "${INSPECT_CMD}"
fi

exec docker exec "${docker_exec_flags[@]}" -w /opt/src/infinito "${container}" sh
