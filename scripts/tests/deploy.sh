#!/usr/bin/env bash
set -euo pipefail

# Compose-based deploy test runner:
# - uses docker-compose.yml (profile "ci") instead of docker run
# - starts coredns + infinito service
# - computes excludes by executing inside the running infinito container
# - runs cli.create.inventory + cli.deploy.dedicated inside the container
# - shuts down compose stack at the end

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TYPE=""
NO_CACHE=0
MISSING_ONLY=0

: "${INFINITO_DISTRO:?INFINITO_DISTRO must be set}"

# -------------------------------------------------------------------
# Config (kept from the previous version)
# -------------------------------------------------------------------

# -------------------------------------------------------------------
# Lifecycle gating
# -------------------------------------------------------------------
# Only these lifecycles are considered "tested" and therefore allowed to run.
# Everything else (including missing lifecycle) will be excluded from the CI deploy.
TESTED_LIFECYCLES="alpha beta rc stable"


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
svc-bkp-rmt-2-loc
svc-opt-keyboard-color
svc-opt-ssd-hdd
web-app-oauth2-proxy
EOF
)}"

usage() {
	cat <<'EOF'
Usage: scripts/tests/deploy.sh --type <server|workstation> --distro <arch|debian|ubuntu|fedora|centos> [options]

Options:
  --no-cache       Rebuild compose image with --no-cache
  --missing        Build only if missing (skip build if image exists)
  -h, --help       Show this help

What it runs (compose-based):
  1) INFINITO_DISTRO=<distro> docker compose --profile ci build (optional)
  2) docker compose --profile ci up -d coredns infinito
  3) Compute excluded roles (invokable-based) + BASE_EXCLUDE + ALWAYS_EXCLUDE
  4) docker compose exec infinito python -m cli.create.inventory ...
  5) docker compose exec infinito python -m cli.deploy.dedicated ...
  6) docker compose --profile ci down
EOF
}

die() {
	echo "[ERROR] $*" >&2
	exit 1
}

trim_lines() { sed -e 's/[[:space:]]\+$//' -e '/^$/d'; }

join_by_comma() {
	local IFS=","
	echo "$*"
}

# -------------------------------------------------------------------
# Compose helpers
# -------------------------------------------------------------------
compose() {
  (
    cd "${REPO_ROOT}"
    INFINITO_DISTRO="${INFINITO_DISTRO}" docker compose --profile ci "$@"
  )
}

infinito_exec() {
  compose exec -T infinito "$@"
}

get_lifecycle_exclude() {
	# We exclude any role whose lifecycle is NOT in TESTED_LIFECYCLES.
	# The lifecycle_filter prints role names space-separated, so convert to newline.
	# NOTE: In blacklist mode, missing lifecycle is included by default -> desired here.
	infinito_exec sh -lc \
		"python3 -m cli.meta.roles.lifecycle_filter blacklist ${TESTED_LIFECYCLES}" \
	| tr ' ' '\n' | trim_lines
}

ensure_compose_image() {
	# Compose image name in docker-compose.yml:
	#   image: "infinito-${INFINITO_DISTRO:-arch}"
	local image="infinito-${INFINITO_DISTRO}"

	if [[ "${MISSING_ONLY}" == "1" ]]; then
		if docker image inspect "${image}" >/dev/null 2>&1; then
			echo ">>> Image already exists: ${image} (skipping build due to --missing)"
			return
		fi
	fi

	if [[ "${NO_CACHE}" == "1" ]]; then
		echo ">>> docker compose build --no-cache infinito (INFINITO_DISTRO=${INFINITO_DISTRO})"
		compose build --no-cache infinito
	else
		echo ">>> docker compose build infinito (INFINITO_DISTRO=${INFINITO_DISTRO})"
		compose build infinito
	fi
}

start_stack() {
  echo ">>> Starting compose stack (coredns + infinito)"
  compose up -d coredns infinito
}

# -------------------------------------------------------------------
# Inventory/exclude logic (now executed via compose exec)
# -------------------------------------------------------------------
get_invokable() {
	infinito_exec sh -lc 'python3 -m cli.meta.applications.invokable' | trim_lines
}

filter_allowed() {
	local type="$1"
	case "$type" in
	workstation)
		grep -E '^(desk-|util-desk-)' || true
		;;
	server)
		grep -E '^web-|svc-db-' || true
		;;
	*)
		die "Unknown deploy type: $type (expected: workstation|server)"
		;;
	esac
}

compute_exclude_csv() {
	local type="$1"
	local all allowed computed combined final
	local drv_exclude
	local lifecycle_exclude
	local -a arr=()

	all="$(get_invokable)" || die "get_invokable failed (cli.meta.applications.invokable not available?)"

	allowed="$(printf "%s\n" "$all" | filter_allowed "$type")"

	computed="$(
		comm -23 \
			<(printf "%s\n" "$all" | LC_ALL=C sort) \
			<(printf "%s\n" "$allowed" | LC_ALL=C sort) |
			trim_lines
	)"

	drv_exclude="$(printf "%s\n" "$all" | grep -E '^drv-' || true)"
	lifecycle_exclude="$(get_lifecycle_exclude || true)"

	combined="$(
		printf "%s\n%s\n%s\n%s\n" \
			"$computed" \
			"$drv_exclude" \
			"$lifecycle_exclude" \
			"$(printf "%s\n" "$BASE_EXCLUDE" | tr ',' '\n')" \
			"$(printf "%s\n" "$ALWAYS_EXCLUDE" | tr ',' '\n')" |
			trim_lines | LC_ALL=C sort -u
	)"

	final="$(
		comm -12 \
			<(printf "%s\n" "$combined" | LC_ALL=C sort) \
			<(printf "%s\n" "$all" | LC_ALL=C sort) |
			trim_lines
	)"

	if [[ -n "${final}" ]]; then
		mapfile -t arr <<<"${final}"
	fi

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
	--type)
		TYPE="${2:-}"
		shift 2
		;;
	--no-cache)
		NO_CACHE=1
		shift
		;;
	--missing)
		MISSING_ONLY=1
		shift
		;;
	-h | --help)
		usage
		exit 0
		;;
	*) die "Unknown argument: $1" ;;
	esac
done

[[ -n "${TYPE}" ]] || die "--type is required"

case "${TYPE}" in
server | workstation ) ;;
*) die "Invalid --type '${TYPE}' (expected: server|workstation)" ;;
esac

case "${INFINITO_DISTRO}" in
arch | debian | ubuntu | fedora | centos) ;;
*) die "Invalid --distro '${INFINITO_DISTRO}' (expected: arch|debian|ubuntu|fedora|centos)" ;;
esac

echo ">>> Deploy type:     ${TYPE}"
echo ">>> Distro:          ${INFINITO_DISTRO}"
echo ">>> Repo root:       ${REPO_ROOT}"

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
pushd "${REPO_ROOT}" >/dev/null

on_exit() {
  rc=$?
  if [[ $rc -ne 0 ]]; then
    echo ">>> ERROR (rc=$rc) - keeping compose stack for debugging."
    echo ">>> Hint:"
    echo "    docker ps"
    echo "    INFINITO_DISTRO=${INFINITO_DISTRO} docker compose --profile ci ps"
    echo "    INFINITO_DISTRO=${INFINITO_DISTRO} docker compose --profile ci logs --tail=200"
  fi
  exit $rc
}
trap on_exit EXIT

ensure_compose_image
start_stack


# ---------------------------------------------------------------------------
# Compute excludes
# ---------------------------------------------------------------------------
EXCLUDE_CSV="$(compute_exclude_csv "${TYPE}")"
echo ">>> Excluded roles:  ${EXCLUDE_CSV:-<none>}"

# ---------------------------------------------------------------------------
# Run inventory generation + deploy INSIDE the compose container
# ---------------------------------------------------------------------------
echo ">>> Creating CI inventory inside compose container..."
infinito_exec sh -lc '
  cd /opt/src/infinito &&
  python3 -m cli.create.inventory \
    /etc/inventories/github-ci \
    --host localhost \
    --ssl-disabled \
    --primary-domain infinito.localhost \
    --exclude "'"${EXCLUDE_CSV}"'" \
    --vars-file inventory.sample.yml \
'

echo ">>> Ensuring vault password file exists..."
infinito_exec sh -lc \
	"mkdir -p /etc/inventories/github-ci && \
	 [ -f /etc/inventories/github-ci/.password ] || \
	 printf '%s\n' 'ci-vault-password' > /etc/inventories/github-ci/.password"

echo ">>> Running deploy via cli.deploy.dedicated inside compose container..."
infinito_exec python3 -m cli.deploy.dedicated \
	/etc/inventories/github-ci/servers.yml \
	-p /etc/inventories/github-ci/.password \
	-vv \
	--assert true \
	--debug \
	--diff \
	-T "${TYPE}"

echo ">>> Deploy test suite finished successfully."

popd >/dev/null
