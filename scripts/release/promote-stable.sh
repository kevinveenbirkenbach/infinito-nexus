#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# SPOT: load global environment from scripts/meta/env.sh
# ------------------------------------------------------------
_env_sh="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/meta/env.sh"

if [[ ! -f "${_env_sh}" ]]; then
  echo "[promote-stable] ERROR: env.sh not found: ${_env_sh}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${_env_sh}"

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${OWNER:?OWNER is required (e.g. github.repository_owner)}"

REGISTRY="${REGISTRY:-ghcr.io}"
REPO_PREFIX="${REPO_PREFIX:-infinito}"
DISTROS="${DISTROS:-arch debian ubuntu fedora centos}"
DEFAULT_DISTRO="${DEFAULT_DISTRO:-arch}"

CI_WORKFLOW_PATH="${CI_WORKFLOW_PATH:-ci-orchestrator.yml}"
CI_LOOKBACK_PAGES="${CI_LOOKBACK_PAGES:-3}"
CI_PER_PAGE="${CI_PER_PAGE:-100}"

repo="${GITHUB_REPOSITORY}"

echo "------------------------------------------------------------"
echo "[promote-stable] repo        = ${repo}"
echo "[promote-stable] registry    = ${REGISTRY}"
echo "[promote-stable] owner       = ${OWNER}"
echo "[promote-stable] repo_prefix = ${REPO_PREFIX}"
echo "[promote-stable] distros     = ${DISTROS}"
echo "[promote-stable] ci_workflow = ${CI_WORKFLOW_PATH}"
echo "[promote-stable] lookback    = pages=${CI_LOOKBACK_PAGES} per_page=${CI_PER_PAGE}"
echo "------------------------------------------------------------"

git fetch --tags --force >/dev/null 2>&1 || true

mapfile -t vtags < <(git tag -l 'v*' | sort -V)
if [[ ${#vtags[@]} -eq 0 ]]; then
  echo "[promote-stable] No v* tags found. Nothing to promote."
  exit 0
fi

ci_succeeded_for_sha() {
  local sha="$1"
  local page=1

  while [[ "${page}" -le "${CI_LOOKBACK_PAGES}" ]]; do
    local result
    result="$(
      TARGET_SHA="${sha}" gh api -H "Accept: application/vnd.github+json" \
        "/repos/${repo}/actions/workflows/${CI_WORKFLOW_PATH}/runs" \
        -f per_page="${CI_PER_PAGE}" \
        -f page="${page}" \
            | "${PYTHON}" -c '
import json, os, sys
target = os.environ["TARGET_SHA"]
data = json.load(sys.stdin)
runs = data.get("workflow_runs", [])
for r in runs:
    if (
        r.get("head_sha") == target
        and r.get("status") == "completed"
        and r.get("conclusion") == "success"
    ):
        print("success")
        sys.exit(0)
print("none")
'
    )" || result="none"

    if [[ "${result}" == "success" ]]; then
      echo "success"
      return 0
    fi

    page=$((page + 1))
  done

  echo "none"
}

candidate_tag=""
candidate_sha=""

for (( i=${#vtags[@]}-1; i>=0; i-- )); do
  t="${vtags[$i]}"
  sha="$(git rev-list -n 1 "${t}")"
  echo "[promote-stable] Checking ${t} (sha=${sha})"

  if [[ "$(ci_succeeded_for_sha "${sha}")" == "success" ]]; then
    candidate_tag="${t}"
    candidate_sha="${sha}"
    echo "[promote-stable] ✅ Candidate found: ${candidate_tag} (${candidate_sha})"
    break
  fi
done

if [[ -z "${candidate_tag}" ]]; then
  echo "[promote-stable] No version tag with successful Nightly CI found. Nothing to promote."
  exit 0
fi

stable_exists=true
stable_sha=""
stable_version=""

if git rev-parse -q --verify "refs/tags/stable" >/dev/null 2>&1; then
  stable_sha="$(git rev-list -n 1 stable)"
  stable_version="$(git tag --points-at "${stable_sha}" -l 'v*' | sort -V | tail -n1 || true)"
else
  stable_exists=false
fi

echo
echo "[promote-stable] Current stable:"
echo "  exists  = ${stable_exists}"
echo "  sha     = ${stable_sha:-<none>}"
echo "  version = ${stable_version:-<none>}"

echo
echo "[promote-stable] Candidate:"
echo "  sha     = ${candidate_sha}"
echo "  version = ${candidate_tag}"

if [[ "${stable_exists}" == "true" && "${stable_sha}" == "${candidate_sha}" ]]; then
  echo "[promote-stable] stable already points to candidate. Nothing to do."
  exit 0
fi

if [[ -n "${stable_version}" ]]; then
  highest="$(printf '%s\n%s\n' "${stable_version}" "${candidate_tag}" | sort -V | tail -n1)"
  if [[ "${highest}" != "${candidate_tag}" ]]; then
    echo "[promote-stable] Candidate is not higher than current stable (${stable_version}). Nothing to do."
    exit 0
  fi
fi

echo

# Verify images exist for candidate tag (NORMAL only)
for distro in ${DISTROS}; do
  img="${REGISTRY}/${OWNER}/${REPO_PREFIX}-${distro}:${candidate_tag}"
  if ! docker manifest inspect "${img}" >/dev/null 2>&1; then
    echo "[promote-stable] ERROR: missing image ${img} -> abort"
    exit 1
  fi
done

echo "[promote-stable] Promoting stable -> ${candidate_tag} (${candidate_sha})"

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

git tag -d stable 2>/dev/null || true
git push origin :refs/tags/stable || true

git tag stable "${candidate_sha}"
git push origin stable

echo "[promote-stable] ✅ Git tag 'stable' updated."

echo
echo "[promote-stable] Promoting GHCR :stable tags from ${candidate_tag}"

for distro in ${DISTROS}; do
  src="${REGISTRY}/${OWNER}/${REPO_PREFIX}-${distro}:${candidate_tag}"
  dst="${REGISTRY}/${OWNER}/${REPO_PREFIX}-${distro}:stable"
  echo "==> ${distro}"
  docker buildx imagetools create -t "${dst}" "${src}"

  if [[ "${distro}" == "${DEFAULT_DISTRO}" ]]; then
    alias="${REGISTRY}/${OWNER}/${REPO_PREFIX}:stable"
    docker buildx imagetools create -t "${alias}" "${src}"
  fi
done

echo
echo "[promote-stable] ✅ GHCR :stable tags updated to ${candidate_tag}"
echo "[promote-stable] Done."
