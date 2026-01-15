#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_REF:?GITHUB_REF is required}"

version_tag="${GITHUB_REF#refs/tags/}"
echo "Updating git tag 'stable' -> ${version_tag}"

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

sha="$(git rev-parse HEAD)"

git tag -d stable 2>/dev/null || true
git push origin :refs/tags/stable || true

git tag stable "${sha}"
git push origin stable

echo "✅ Stable git tag updated to ${version_tag}."
