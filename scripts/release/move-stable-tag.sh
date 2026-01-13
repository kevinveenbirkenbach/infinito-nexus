#!/usr/bin/env bash
set -euo pipefail

# Move git tag "stable" to the current commit SHA.
# Requires: GITHUB_REF, GITHUB_SHA

: "${GITHUB_REF:?GITHUB_REF is required}"
: "${GITHUB_SHA:?GITHUB_SHA is required}"

version_tag="${GITHUB_REF#refs/tags/}"
echo "Updating git tag 'stable' -> ${version_tag} (${GITHUB_SHA})"

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

git tag -d stable 2>/dev/null || true
git push origin :refs/tags/stable || true

git tag stable "${GITHUB_SHA}"
git push origin stable

echo "✅ Stable git tag updated to ${version_tag}."
