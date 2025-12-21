#!/usr/bin/env bash
set -euo pipefail

# Variant B (local-image + excludes):
# - Build the local Infinito.Nexus Docker image via Makefile (make build/build-no-cache/build-missing)
# - Use ONLY that local image tag (e.g. infinito-arch) for the deploy container (no pulling pkgmgr images)
# - Compute excluded roles automatically based on "invokable" roles and the selected type
# - Run the real deploy via: python3 -m cli.deploy.container run ...
#
# It uses cli/deploy/container.py which supports:
#   python3 -m cli.deploy.container run [container-opts] -- [inventory-args ...] -- [deploy-args ...]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

TYPE=""
DISTRO=""
IMAGE=""
NO_CACHE=0
MISSING_ONLY=0

# -------------------------------------------------------------------
# Config (kept from the previous version)
# -------------------------------------------------------------------
MASK_CREDENTIALS_IN_LOGS_DEFAULT="false"
MASK_CREDENTIALS_IN_LOGS="${MASK_CREDENTIALS_IN_LOGS:-$MASK_CREDENTIALS_IN_LOGS_DEFAULT}"

AUTHORIZED_KEYS_DEFAULT="ssh-ed25519 AAAA_TEST_DUMMY_KEY github-ci-dummy@infinito"
AUTHORIZED_KEYS="${AUTHORIZED_KEYS:-$AUTHORIZED_KEYS_DEFAULT}"

# Optional: allow adding additional excludes globally (comma-separated or newline-separated)
ALWAYS_EXCLUDE="${ALWAYS_EXCLUDE:-}"

# Central excludes (same everywhere) - can be comma-separated or newline-separated.
BASE_EXCLUDE="${BASE_EXCLUDE:-$(
  cat <<'EOF'
drv-lid-switch
svc-db-memcached
svc-db-redis
svc-net-wireguard-core
svc-net-wireguard-firewalled
svc-net-wireguard-plain
svc-bkp-loc-2-usb
svc-bkp-rmt-2-loc
svc-opt-keyboard-color
svc-opt-ssd-hdd
web-app-bridgy-fed
web-app-oauth2-proxy
web-app-postmarks
web-app-elk
web-app-syncope
web-app-socialhome
web-svc-xmpp
EOF
)}"

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
  2) Compute excluded roles (invokable-based) + BASE_EXCLUDE + ALWAYS_EXCLUDE
  3) python3 -m cli.deploy.container run --image <local-image> -- [inventory-args] -- [deploy-args]
EOF
}

die() { echo "[ERROR] $*" >&2; exit 1; }

trim_lines() { sed -e 's/[[:space:]]\+$//' -e '/^$/d'; }

join_by_comma() {
  local IFS=","
  echo "$*"
}

get_invokable() {
  set -o pipefail
  docker run --rm \
    -e NIX_CONFIG="${NIX_CONFIG}" \
    -v "${REPO_ROOT}:/opt/src/infinito" \
    -w /opt/src/infinito \
    "${IMAGE}" \
    python3 -m cli.meta.applications.invokable 2>/dev/null | trim_lines
}

filter_allowed() {
  local type="$1"
  case "$type" in
    workstation)
      # desk-* and util-desk-*
      grep -E '^(desk-|util-desk-)' || true
      ;;
    server)
      # web-* (includes web-app-*, web-svc-*, etc.)
      grep -E '^web-' || true
      ;;
    universal)
      cat
      ;;
    *)
      die "Unknown deploy type: $type (expected: workstation|server|universal)"
      ;;
  esac
}

compute_exclude_csv() {
  local type="$1"

  local all allowed computed combined final

  all="$(get_invokable)";
  if ! all="$(get_invokable)"; then
    echo "Required module cli.meta.applications.invokable does not exist (or get_invokable failed)"
  fi
  allowed="$(printf "%s\n" "$all" | filter_allowed "$type")"

  # computed = all - allowed
  computed="$(comm -23 <(printf "%s\n" "$all" | sort) <(printf "%s\n" "$allowed" | sort) | trim_lines)"

  # combined = computed ∪ BASE_EXCLUDE ∪ ALWAYS_EXCLUDE
  combined="$(
    printf "%s\n%s\n%s\n" \
      "$computed" \
      "$(printf "%s\n" "$BASE_EXCLUDE" | tr ',' '\n')" \
      "$(printf "%s\n" "$ALWAYS_EXCLUDE" | tr ',' '\n')" \
    | trim_lines | sort -u
  )"

  # final = combined ∩ all   (keep only invokable names)
  final="$(comm -12 <(printf "%s\n" "$combined" | sort) <(printf "%s\n" "$all" | sort) | trim_lines)"

  # To comma-separated
  # shellcheck disable=SC2206
  local arr=($final)
  if [[ ${#arr[@]} -eq 0 ]]; then
    echo ""
  else
    join_by_comma "${arr[@]}"
  fi
}

# -------------------------------------------------------------------
# Args
# -------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --type)      TYPE="${2:-}"; shift 2 ;;
    --distro)    DISTRO="${2:-}"; shift 2 ;;
    --image)     IMAGE="${2:-}"; shift 2 ;;
    --no-cache)  NO_CACHE=1; shift ;;
    --missing)   MISSING_ONLY=1; shift ;;
    -h|--help)   usage; exit 0 ;;
    *) die "Unknown argument: $1" ;;
  esac
done

[[ -n "${TYPE}" ]]   || die "--type is required"
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

# ---------------------------------------------------------------------------
# Build local image via Makefile
# ---------------------------------------------------------------------------
echo ">>> Deploy type:     ${TYPE}"
echo ">>> Distro:          ${DISTRO}"
echo ">>> Local image:     ${IMAGE}"
echo ">>> Repo root:       ${REPO_ROOT}"

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

docker image inspect "${IMAGE}" >/dev/null 2>&1 || die "Local image not found after build: ${IMAGE}"

# ---------------------------------------------------------------------------
# Compute excludes (restored)
# ---------------------------------------------------------------------------
EXCLUDE_CSV="$(compute_exclude_csv "${TYPE}")"
echo ">>> Excluded roles:  ${EXCLUDE_CSV:-<none>}"

echo ">>> Preflight: entry.sh inside ${IMAGE}"
docker run \
  -e NIX_CONFIG="${NIX_CONFIG}" \
  --rm \
  --entrypoint bash "${IMAGE}" -lc '
  set -euo pipefail
  ls -la /opt/src/infinito/scripts/docker/entry.sh
  sha256sum /opt/src/infinito/scripts/docker/entry.sh | head -n1
'

# ---------------------------------------------------------------------------
# Run deploy via container runner
#   container run -- [inventory-args ...] -- [deploy-args ...]
# ---------------------------------------------------------------------------
echo ">>> Running deploy via cli.deploy.container (local image only)..."
python3 -m cli.deploy.container run \
  --image "${IMAGE}" \
  -- \
  --exclude "${EXCLUDE_CSV}" \
  --vars "{\"MASK_CREDENTIALS_IN_LOGS\": ${MASK_CREDENTIALS_IN_LOGS}}" \
  --authorized-keys "${AUTHORIZED_KEYS}" \
  -- \
  -T "${TYPE}"

popd >/dev/null
echo ">>> Deploy test suite finished successfully."
