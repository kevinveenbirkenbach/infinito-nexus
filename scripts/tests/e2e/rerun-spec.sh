#!/usr/bin/env bash
# Rerun a role-local Playwright spec against the live running stack.
#
# Preconditions:
#   - The role has been deployed at least once, so the Playwright project is
#     staged under $TEST_E2E_PLAYWRIGHT_STAGE_BASE_DIR/<role> with a rendered
#     .env file.
#   - The application under test is still running.
#
# This script intentionally does NOT re-render .env and does NOT re-stage the
# project. It only overwrites tests/playwright.spec.js from the repo and
# reruns Playwright via the same container image the deploy-time runner uses.
#
# Usage:
#   scripts/tests/e2e/rerun-spec.sh <role> [playwright args...]
#   scripts/tests/e2e/rerun-spec.sh web-app-nextcloud --grep "talk admin"
set -euo pipefail

if [[ $# -lt 1 ]]; then
	echo "usage: $0 <role> [playwright args...]" >&2
	exit 2
fi

role="$1"
shift

repo_root="$(cd "$(dirname "$0")/../../.." && pwd)"
spec_src="$repo_root/roles/$role/files/playwright.spec.js"
defaults="$repo_root/roles/test-e2e-playwright/defaults/main.yml"
package_json="$repo_root/roles/test-e2e-playwright/files/package.json"

stage_base="${TEST_E2E_PLAYWRIGHT_STAGE_BASE_DIR:-/tmp/test-e2e-playwright}"
reports_base="${TEST_E2E_PLAYWRIGHT_REPORTS_BASE_DIR:-/var/lib/infinito/logs/test-e2e-playwright}"
distro="${TEST_E2E_PLAYWRIGHT_IMAGE_DISTRO:-noble}"

stage_dir="$stage_base/$role"
reports_dir="$reports_base/$role"
env_file="$stage_dir/.env"

[[ -f "$spec_src" ]] || {
	echo "missing spec: $spec_src" >&2
	exit 1
}
[[ -d "$stage_dir" ]] || {
	echo "missing staging dir (run deploy first): $stage_dir" >&2
	exit 1
}
[[ -f "$env_file" ]] || {
	echo "missing rendered env (run deploy first): $env_file" >&2
	exit 1
}

image="${TEST_E2E_PLAYWRIGHT_IMAGE:-}"
if [[ -z "$image" ]]; then
	base_image="$(awk '/^[[:space:]]*image:/{print $2; exit}' "$defaults")"
	version="$(awk -F'"' '/@playwright\/test/{print $4; exit}' "$package_json")"
	version="${version#^}"
	version="${version#~}"
	image="${base_image}:v${version}-${distro}"
fi

command -v docker >/dev/null || {
	echo "docker not found in PATH" >&2
	exit 1
}

mkdir -p "$stage_dir/tests" "$stage_dir/volume" "$reports_dir"
cp "$spec_src" "$stage_dir/tests/playwright.spec.js"

cmd="${TEST_E2E_PLAYWRIGHT_COMMAND:-npm install --no-fund --no-audit && npx playwright test${*:+ $*}}"

exec docker run --rm \
	--ipc=host --shm-size=1g \
	--env-file "$env_file" \
	-v "$stage_dir:/e2e" \
	-v "$stage_dir/volume:/volume" \
	-v "$reports_dir:/reports" \
	-w /e2e \
	"$image" \
	/bin/bash -lc "$cmd"
