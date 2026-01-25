#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

TYPE=""
APP=""
KEEP_STACK_ON_FAILURE=0
DEBUG=0

: "${INFINITO_DISTRO:?INFINITO_DISTRO must be set (e.g. INFINITO_DISTRO=arch)}"

usage() {
  cat <<'EOF'
Usage:
  INFINITO_DISTRO=<distro> scripts/tests/deploy/ci/distros.sh --type <server|workstation|universal> [options]

Options:
  --app <application_id>  REQUIRED now (server and workstation)
  --keep-stack-on-failure Keep compose stack up on failure (for debugging)
  --debug                 Enable Ansible debug mode
  --no-debug              Disable Ansible debug mode (default)
  -h, --help              Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --type) TYPE="${2:-}"; shift 2 ;;
    --app) APP="${2:-}"; shift 2 ;;
    --keep-stack-on-failure) KEEP_STACK_ON_FAILURE=1; shift ;;
    --debug) DEBUG=1; shift ;;
    --no-debug) DEBUG=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "[ERROR] Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

[[ -n "${TYPE}" ]] || { echo "[ERROR] --type is required" >&2; usage; exit 2; }
[[ -n "${APP}"  ]] || { echo "[ERROR] --app is required now" >&2; usage; exit 2; }

cd "${REPO_ROOT}"

args=( "--type" "${TYPE}" "--logs-dir" "logs" )
args+=( "--distro" "${INFINITO_DISTRO}" )
args+=( "--app" "${APP}" )
if [[ "${KEEP_STACK_ON_FAILURE}" == "1" ]]; then args+=( "--keep-stack-on-failure" ); fi
if [[ "${DEBUG}" == "1" ]]; then args+=( "--debug" ); else args+=( "--no-debug" ); fi

"${PYTHON}" -m cli.deploy.development run "${args[@]}"
