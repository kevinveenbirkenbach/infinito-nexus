#!/usr/bin/env bash
set -euo pipefail

# -------------------------------------------------------------------
# Config (safe defaults)
# -------------------------------------------------------------------
MASK_CREDENTIALS_IN_LOGS="${MASK_CREDENTIALS_IN_LOGS:-false}"
DEPLOY_TARGET="${DEPLOY_TARGET:-server}"
AUTHORIZED_KEYS="${AUTHORIZED_KEYS:-ssh-ed25519 AAAA_TEST_DUMMY_KEY github-ci-dummy@infinito}"

ALWAYS_EXCLUDE="${ALWAYS_EXCLUDE:-}"

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

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
die() { echo "[ERROR] $*" >&2; exit 1; }
trim_lines() { sed -e 's/[[:space:]]\+$//' -e '/^$/d'; }

# -------------------------------------------------------------------
# Args
# -------------------------------------------------------------------
DEPLOY_TYPE=""
DISTRO=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --type)   DEPLOY_TYPE="$2"; shift 2 ;;
    --distro) DISTRO="$2"; shift 2 ;;
    *) die "Unknown arg: $1" ;;
  esac
done

[[ -n "${DEPLOY_TYPE}" ]] || die "Missing --type workstation|server|universal"
[[ -n "${DISTRO}" ]] || die "Missing --distro arch|debian|ubuntu|fedora|centos"

CONTROLLER_IMAGE="infinito-${DISTRO}"

echo ">>> Deploy type: ${DEPLOY_TYPE}"
echo ">>> Distro:      ${DISTRO}"
echo ">>> Target:      ${DEPLOY_TARGET}"
echo ">>> Controller: ${CONTROLLER_IMAGE}"

# -------------------------------------------------------------------
# Ensure controller image
# -------------------------------------------------------------------
echo ">>> Ensuring controller image exists (missing-only)"
INFINITO_DISTRO="${DISTRO}" bash scripts/build/image.sh --missing --tag "${CONTROLLER_IMAGE}"

# -------------------------------------------------------------------
# Controller run (localhost deploy, NO ssh, NO target container)
# -------------------------------------------------------------------
docker run --rm \
  --network=host \
  -e DEPLOY_TYPE="${DEPLOY_TYPE}" \
  -e DEPLOY_TARGET="${DEPLOY_TARGET}" \
  -e MASK_CREDENTIALS_IN_LOGS="${MASK_CREDENTIALS_IN_LOGS}" \
  -e AUTHORIZED_KEYS="${AUTHORIZED_KEYS}" \
  -e BASE_EXCLUDE="${BASE_EXCLUDE}" \
  -e ALWAYS_EXCLUDE="${ALWAYS_EXCLUDE}" \
  -v "$(pwd):/opt/src/infinito" \
  -w /opt/src/infinito \
  "${CONTROLLER_IMAGE}" \
  bash -lc '
    set -euo pipefail

    : "${MASK_CREDENTIALS_IN_LOGS:=false}"

    die() { echo "[ERROR] $*" >&2; exit 1; }
    trim_lines() { sed -e "s/[[:space:]]\+$//" -e "/^$/d"; }

    infinito --help >/dev/null || die "infinito missing"

    get_invokable() {
      infinito meta applications invokable | trim_lines
    }

    filter_allowed() {
      case "$1" in
        workstation) grep -E "^(desk-|util-desk-)" || true ;;
        server)      grep -E "^web-" || true ;;
        universal)   cat ;;
        *) die "Invalid DEPLOY_TYPE: $1" ;;
      esac
    }

    compute_exclude_csv() {
      tmp="$(mktemp -d)"
      all="$tmp/all"
      allowed="$tmp/allowed"
      combined="$tmp/combined"

      get_invokable | sort >"$all"
      get_invokable | filter_allowed "$DEPLOY_TYPE" | sort >"$allowed"

      comm -23 "$all" "$allowed" >"$combined"

      printf "%s\n%s\n" "$BASE_EXCLUDE" "$ALWAYS_EXCLUDE" \
        | tr "," "\n" >>"$combined"

      sort -u "$combined" | comm -12 - "$all" | paste -sd, -
      rm -rf "$tmp"
    }

    EXCLUDE_CSV="$(compute_exclude_csv)"
    echo ">>> Excluded roles: ${EXCLUDE_CSV:-<none>}"

    # ------------------------------------------------------------
    # Inventory: localhost (NO SSH)
    # ------------------------------------------------------------
    mkdir -p inventories/github-ci

    cat > inventories/github-ci/servers.yml <<YML
all:
  hosts:
    localhost:
      ansible_connection: local
YML

    printf "ci-vault-password\n" > inventories/github-ci/.password

    run_round() {
      local name="$1"; shift
      echo "============================================================"
      echo ">>> ${name}"
      echo "============================================================"

      python3 -m cli.deploy.dedicated \
        inventories/github-ci/servers.yml \
        -p inventories/github-ci/.password \
        --exclude "${EXCLUDE_CSV}" \
        --vars "{\"MASK_CREDENTIALS_IN_LOGS\": ${MASK_CREDENTIALS_IN_LOGS}}" \
        --authorized-keys "${AUTHORIZED_KEYS}" \
        -- \
        -T "${DEPLOY_TARGET}" "$@"
    }

    run_round "[1/3] First deploy (debug)" \
      --debug --skip-cleanup --skip-tests

    run_round "[2/3] Second deploy (--reset)" \
      --reset --debug --skip-cleanup --skip-tests

    run_round "[3/3] Third deploy (async)" \
      --skip-cleanup --skip-tests

    echo ">>> Done."
  '
