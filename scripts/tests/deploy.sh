#!/usr/bin/env bash
set -euo pipefail

# scripts/tests/deploy.sh
#
# Variant B (fixed):
# - Build the local Infinito.Nexus Docker image via Makefile (make build/build-no-cache/build-missing)
# - Use ONLY that local image tag (e.g. infinito-arch) for the deploy container
# - Run the real deploy via: python3 -m cli.deploy.container run ...
#
# NOTE:
# This script does NOT call `infinito deploy ...` (your CLI doesn't have that).
# It uses your existing container runner in cli/deploy/container.py.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

TYPE=""
DISTRO=""
IMAGE=""          # default: infinito-<distro>
NO_CACHE=0
MISSING_ONLY=0

usage() {
  cat <<'EOF'
Usage: scripts/tests/deploy.sh --type <server|workstation|universal> --distro <arch|debian|ubuntu|fedora|centos> [options]

Options:
  --image <name>   Use a specific local image tag (no pull). Default: infinito-<distro>
  --no-cache       Rebuild image with --no-cache (make build-no-cache)
  --missing        Build only if missing (make build-missing)
  -h, --help       Show this help

What it runs:
  1) INFINITO_DISTRO=<distro> make build|build-no-cache|build-missing
  2) python3 -m cli.deploy.container run --image <local-image> -- -T <type>
EOF
}

die() { echo "[ERROR] $*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --type)   TYPE="${2:-}"; shift 2 ;;
    --distro) DISTRO="${2:-}"; shift 2 ;;
    --image)  IMAGE="${2:-}"; shift 2 ;;
    --no-cache) NO_CACHE=1; shift ;;
    --missing)  MISSING_ONLY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown argument: $1" ;;
  esac
done

[[ -n "${TYPE}" ]]  || die "--type is required"
[[ -n "${DISTRO}" ]] || die "--distro is required"

case "${TYPE}" in
  server|workstation|universal) ;;
  *) die "Invalid --type '${TYPE}' (expected: server|workstation|universal)" ;;
esac

case "${DISTRO}" in
  arch|debian|ubuntu|fedora|centos) ;;
  *) die "Invalid --distro '${DISTRO}' (expected: arch|debian|ubuntu|fedora|centos)" ;;
esac

if [[ -z "${IMAGE}" ]]; then
  IMAGE="infinito-${DISTRO}"
fi

echo ">>> Deploy type:   ${TYPE}"
echo ">>> Distro:        ${DISTRO}"
echo ">>> Local image:   ${IMAGE}"
echo ">>> Repo root:     ${REPO_ROOT}"

# ---------------------------------------------------------------------------
# 1) Build local image via Makefile
# ---------------------------------------------------------------------------
pushd "${REPO_ROOT}" >/dev/null

if [[ "${NO_CACHE}" == "1" ]]; then
  echo ">>> make build-no-cache (INFINITO_DISTRO=${DISTRO})"
  INFINITO_DISTRO="${DISTRO}" make build-no-cache
elif [[ "${MISSING_ONLY}" == "1" ]]; then
  echo ">>> make build-missing (INFINITO_DISTRO=${DISTRO})"
  INFINITO_DISTRO="${DISTRO}" make build-missing
else
  echo ">>> make build (INFINITO_DISTRO=${DISTRO})"
  INFINITO_DISTRO="${DISTRO}" make build
fi

# Ensure the image exists locally
docker image inspect "${IMAGE}" >/dev/null 2>&1 || die "Local image not found after build: ${IMAGE}"

# ---------------------------------------------------------------------------
# 2) Run deploy via your existing container runner
# ---------------------------------------------------------------------------
#
# cli/deploy/container.py expects:
#   python3 -m cli.deploy.container run [container-opts] -- [deploy-args]
#
# We provide deploy args as:
#   -T <type>
#
echo ">>> Running deploy via cli.deploy.container (local image only)..."
python3 -m cli.deploy.container run \
  --image "${IMAGE}" \
  -- \
  -T "${TYPE}"

popd >/dev/null

echo ">>> Deploy test suite finished successfully."
