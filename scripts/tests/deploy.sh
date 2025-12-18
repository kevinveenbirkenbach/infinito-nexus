#!/usr/bin/env bash
set -euo pipefail

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
MASK_CREDENTIALS_IN_LOGS_DEFAULT="false"
MASK_CREDENTIALS_IN_LOGS="${MASK_CREDENTIALS_IN_LOGS:-$MASK_CREDENTIALS_IN_LOGS_DEFAULT}"

AUTHORIZED_KEYS_DEFAULT="ssh-ed25519 AAAA_TEST_DUMMY_KEY github-ci-dummy@infinito"
AUTHORIZED_KEYS="${AUTHORIZED_KEYS:-$AUTHORIZED_KEYS_DEFAULT}"

DEPLOY_TARGET_DEFAULT="server"
DEPLOY_TARGET="${DEPLOY_TARGET:-$DEPLOY_TARGET_DEFAULT}"

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

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
die() { echo "[ERROR] $*" >&2; exit 1; }

join_by_comma() {
  local IFS=","
  echo "$*"
}

trim_lines() {
  sed -e 's/[[:space:]]\+$//' -e '/^$/d'
}

get_invokable() {
  if command -v infinito >/dev/null 2>&1; then
    infinito meta applications invokable | trim_lines
    return 0
  fi

  # Best-effort fallback: if your repo exposes a python module for this.
  if python3 -c "import cli" >/dev/null 2>&1; then
    python3 -m cli.meta.applications invokable 2>/dev/null | trim_lines || true
    return 0
  fi

  die "Cannot list invokable applications (neither 'infinito' nor usable python module found)."
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
  all="$(get_invokable)"
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

run_deploy() {
  local image="$1"
  local exclude_csv="$2"
  shift 2

  python3 -m cli.deploy.container run --image "$image" "$@" -- \
    --exclude "$exclude_csv" \
    --vars "{\"MASK_CREDENTIALS_IN_LOGS\": ${MASK_CREDENTIALS_IN_LOGS}}" \
    --authorized-keys "$AUTHORIZED_KEYS" \
    -- \
    -T "$DEPLOY_TARGET"
}

# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
DEPLOY_TYPE=""
DISTRO=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --type)  DEPLOY_TYPE="${2:-}"; shift 2 ;;
    --distro) DISTRO="${2:-}"; shift 2 ;;
    --target) DEPLOY_TARGET="${2:-}"; shift 2 ;;
    --) shift; break ;;
    *) die "Unknown arg: $1" ;;
  esac
done

[[ -n "$DEPLOY_TYPE" ]] || die "Missing --type workstation|server|universal"
[[ -n "$DISTRO" ]] || die "Missing --distro arch|debian|ubuntu|fedora|centos"

case "$DISTRO" in
  arch|debian|ubuntu|fedora|centos) ;;
  *) die "Unsupported distro: $DISTRO" ;;
esac

IMAGE="ghcr.io/kevinveenbirkenbach/pkgmgr-${{ $DISTRO }}-virgin:stable"
EXCLUDE_CSV="$(compute_exclude_csv "$DEPLOY_TYPE")"

echo ">>> Deploy type:     $DEPLOY_TYPE"
echo ">>> Distro:          $DISTRO"
echo ">>> Target:          $DEPLOY_TARGET"
echo ">>> Image:           $IMAGE"
echo ">>> Excluded roles:  ${EXCLUDE_CSV:-<none>}"

# -------------------------------------------------------------------
# 1) First deploy: normal + debug (with build)
# -------------------------------------------------------------------
echo ">>> [1/3] First deploy (normal + debug, with build)"
run_deploy "$IMAGE" "$EXCLUDE_CSV" --build -- --debug --skip-cleanup --skip-tests

# -------------------------------------------------------------------
# 2) Second deploy: reset + debug (without build)
# -------------------------------------------------------------------
echo ">>> [2/3] Second deploy (--reset --debug, reuse image)"
run_deploy "$IMAGE" "$EXCLUDE_CSV" -- --reset --debug --skip-cleanup --skip-tests

# -------------------------------------------------------------------
# 3) Third deploy: async deploy – no debug (reuse image)
# -------------------------------------------------------------------
echo ">>> [3/3] Third deploy (async deploy – no debug)"
run_deploy "$IMAGE" "$EXCLUDE_CSV" -- --skip-cleanup --skip-tests
