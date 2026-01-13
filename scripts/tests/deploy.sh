#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

TYPE=""
NO_CACHE=0
MISSING_ONLY=0
APP=""
KEEP_STACK_ON_FAILURE=0

: "${INFINITO_DISTRO:?INFINITO_DISTRO must be set (e.g. INFINITO_DISTRO=arch)}"

usage() {
  cat <<'EOF'
Usage:
  INFINITO_DISTRO=<distro> scripts/tests/deploy.sh --type <server|workstation> [options]

Options:
  --no-cache              Rebuild compose image with --no-cache
  --missing               Build only if missing (skip build if image exists)
  --app <application_id>  REQUIRED now (server and workstation)
  --keep-stack-on-failure Keep compose stack up on failure (for debugging)
  -h, --help              Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --type) TYPE="${2:-}"; shift 2 ;;
    --no-cache) NO_CACHE=1; shift ;;
    --missing) MISSING_ONLY=1; shift ;;
    --app) APP="${2:-}"; shift 2 ;;
    --keep-stack-on-failure) KEEP_STACK_ON_FAILURE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "[ERROR] Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

[[ -n "${TYPE}" ]] || { echo "[ERROR] --type is required" >&2; usage; exit 2; }
[[ -n "${APP}"  ]] || { echo "[ERROR] --app is required now" >&2; usage; exit 2; }

cd "${REPO_ROOT}"

args=( "--type" "${TYPE}" "--logs-dir" "logs" )
args+=( "--distro" "${INFINITO_DISTRO}" )

if [[ "${NO_CACHE}" == "1" ]]; then args+=( "--no-cache" ); fi
if [[ "${MISSING_ONLY}" == "1" ]]; then args+=( "--missing" ); fi
args+=( "--app" "${APP}" )
if [[ "${KEEP_STACK_ON_FAILURE}" == "1" ]]; then args+=( "--keep-stack-on-failure" ); fi

python3 -m cli.deploy.test "${args[@]}"
