#!/usr/bin/env bash
# shellcheck shell=bash
# Restore agent skills from skills-lock.json for reproducible installs.
# Supports Claude Code, Codex, Gemini CLI, Cursor, Copilot, Windsurf, Cline, and more.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

log() { printf '%s\n' "$*"; }
warn() { printf '%s\n' "$*" >&2; }

if ! command -v npx &>/dev/null; then
	warn "skills: npx not found — skipping installation."
	warn "Install Node.js to enable skills: https://nodejs.org"
	exit 0
fi

cd "${REPO_ROOT}"
log "skills: restoring from skills-lock.json..."
npx --yes skills experimental_install
log "skills: installation complete."
