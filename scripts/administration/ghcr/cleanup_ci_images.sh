#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  cleanup_ci_images.sh [--days N] [--owner OWNER] [--distros "arch debian ..."]

Deletes GHCR container package versions that are:
- older than N days (default: 7)
- AND have tags
- AND ALL tags start with "ci-"
So versions with any non-ci tag (e.g. latest, v1.2.3) are preserved.

Robust for USER and ORG owners:
- Tries /orgs/<OWNER>/... first, falls back to /users/<OWNER>/...

Requires:
  - gh CLI authenticated (GH_TOKEN env works)
  - jq installed

Env:
  DAYS, OWNER, DISTROS can be used as defaults.

Examples:
  DAYS=14 OWNER=myorg ./scripts/administration/ghcr/cleanup_ci_images.sh
  ./scripts/administration/ghcr/cleanup_ci_images.sh --days 7 --owner kevinveenbirkenbach
USAGE
}

DAYS="${DAYS:-7}"
OWNER="${OWNER:-}"
DISTROS="${DISTROS:-arch debian ubuntu fedora centos}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --days) DAYS="${2:-}"; shift 2 ;;
    --owner) OWNER="${2:-}"; shift 2 ;;
    --distros) DISTROS="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "${OWNER}" ]]; then
  echo "ERROR: OWNER is required (env OWNER or --owner)." >&2
  exit 2
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI not found." >&2
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq not found." >&2
  exit 1
fi

cutoff="$(date -u -d "${DAYS} days ago" +%s)"
echo ">>> OWNER=${OWNER}"
echo ">>> DAYS=${DAYS}"
echo ">>> cutoff_epoch=${cutoff}"
echo ">>> DISTROS=${DISTROS}"
echo

# --- GH API helpers ---------------------------------------------------------

# Try orgs first, fall back to users
gh_api_json() {
  local method="$1"; shift
  local endpoint="$1"; shift
  local scope="$1"; shift # orgs|users

  if [[ "${method}" == "GET" ]]; then
    gh api -H "Accept: application/vnd.github+json" "/${scope}/${OWNER}/${endpoint}" "$@" 2>/dev/null || true
  else
    gh api -X "${method}" -H "Accept: application/vnd.github+json" "/${scope}/${OWNER}/${endpoint}" "$@" 2>/dev/null || true
  fi
}

# Determine whether OWNER is org or user.
# We keep it simple and resilient:
# - prefer orgs endpoint for container packages; if first request returns JSON array, treat as org
# - otherwise try users endpoint; if that returns JSON array, treat as user
# Returns: "orgs" or "users" on stdout.
detect_scope_for_pkg() {
  local pkg="$1"
  local endpoint="packages/container/${pkg}/versions?per_page=1&page=1"

  local r
  r="$(gh_api_json GET "${endpoint}" orgs)"
  if [[ -n "${r}" ]] && echo "${r}" | jq -e 'type=="array"' >/dev/null 2>&1; then
    echo "orgs"
    return 0
  fi

  r="$(gh_api_json GET "${endpoint}" users)"
  if [[ -n "${r}" ]] && echo "${r}" | jq -e 'type=="array"' >/dev/null 2>&1; then
    echo "users"
    return 0
  fi

  # unknown (no access / package missing). default to orgs (safe), caller will handle empties.
  echo "orgs"
}

list_versions() {
  local pkg="$1"
  local scope
  scope="$(detect_scope_for_pkg "${pkg}")"

  local page=1
  while :; do
    resp="$(gh_api_json GET "packages/container/${pkg}/versions?per_page=100&page=${page}" "${scope}")"

    if [[ -z "${resp}" ]] || [[ "${resp}" == "[]" ]]; then
      break
    fi

    echo "${resp}"

    count="$(echo "${resp}" | jq 'length')"
    if [[ "${count}" -lt 100 ]]; then
      break
    fi
    page=$((page+1))
  done
}

delete_version() {
  local pkg="$1"
  local id="$2"

  # Try orgs first
  if gh api -X DELETE -H "Accept: application/vnd.github+json" \
      "/orgs/${OWNER}/packages/container/${pkg}/versions/${id}" >/dev/null 2>&1; then
    return 0
  fi

  # Fallback to users
  gh api -X DELETE -H "Accept: application/vnd.github+json" \
    "/users/${OWNER}/packages/container/${pkg}/versions/${id}" >/dev/null
}

# --- main -------------------------------------------------------------------

for d in ${DISTROS}; do
  pkg="infinito-${d}"
  echo "=== Package: ${pkg} ==="

  all="$(list_versions "${pkg}" | jq -s 'add' 2>/dev/null || echo '[]')"
  total="$(echo "${all}" | jq 'length')"
  echo "Found versions: ${total}"

  if [[ "${total}" -eq 0 ]]; then
    echo "Skip: no versions (or package not found / no access)"
    echo
    continue
  fi

  deletable="$(echo "${all}" | jq --argjson cutoff "${cutoff}" '
    map(
      . as $v
      | ($v.created_at | fromdateiso8601) as $created
      | ($v.metadata.container.tags // []) as $tags
      | {
          id: $v.id,
          created_at: $v.created_at,
          created_epoch: $created,
          tags: $tags
        }
    )
    | map(select(.created_epoch < $cutoff))
    | map(select((.tags | length) > 0))
    | map(select((.tags | all(startswith("ci-")))))
  ')"

  del_count="$(echo "${deletable}" | jq 'length')"
  echo "Deletable versions: ${del_count}"

  if [[ "${del_count}" -eq 0 ]]; then
    echo "Nothing to delete."
    echo
    continue
  fi

  echo "${deletable}" | jq -r '.[] | "DELETE id=\(.id) created_at=\(.created_at) tags=\(.tags|join(","))"'

  echo "${deletable}" | jq -r '.[].id' | while read -r id; do
    echo "Deleting ${pkg} version id=${id} ..."
    delete_version "${pkg}" "${id}"
  done

  echo "Done: ${pkg}"
  echo
done

echo ">>> Cleanup finished."
