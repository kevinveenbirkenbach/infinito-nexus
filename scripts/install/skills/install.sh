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

# Claude Code discovers project skills in .claude/skills/, but `skills experimental_install`
# writes to .agents/skills/. Symlink .claude/skills -> .agents/skills so Claude Code picks them up.
skills_src="${REPO_ROOT}/.agents/skills"
skills_link="${REPO_ROOT}/.claude/skills"

if [[ ! -d "${skills_src}" ]]; then
	warn "skills: ${skills_src} not found — skipping .claude/skills symlink."
	exit 0
fi

mkdir -p "${REPO_ROOT}/.claude"

if [[ -L "${skills_link}" ]]; then
	ln -sfn "../.agents/skills" "${skills_link}"
elif [[ -e "${skills_link}" ]]; then
	warn "skills: ${skills_link} exists and is not a symlink — skipping."
else
	ln -s "../.agents/skills" "${skills_link}"
fi
log "skills: linked .claude/skills -> ../.agents/skills. Restart Claude Code to load new skills."
