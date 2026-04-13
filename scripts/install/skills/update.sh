#!/usr/bin/env bash
# shellcheck shell=bash
# Update all agent skills to their latest versions and refresh skills-lock.json.
# Reads unique sources from skills-lock.json and re-runs skills add for each.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

log() { printf '%s\n' "$*"; }
warn() { printf '%s\n' "$*" >&2; }

if ! command -v npx &>/dev/null; then
	warn "skills: npx not found — cannot update."
	warn "Install Node.js to enable skills: https://nodejs.org"
	exit 1
fi

if ! command -v jq &>/dev/null; then
	warn "skills: jq not found — cannot parse skills-lock.json."
	exit 1
fi

cd "${REPO_ROOT}"

lockfile="skills-lock.json"
if [[ ! -f "${lockfile}" ]]; then
	warn "skills: ${lockfile} not found in ${REPO_ROOT}."
	exit 1
fi

log "skills: updating from ${lockfile}..."
jq -r '.skills[].source' "${lockfile}" | sort -u | while read -r source; do
	log "skills: updating ${source}..."
	npx --yes skills add --yes "${source}"
done
log "skills: update complete."
