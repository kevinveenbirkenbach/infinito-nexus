#!/usr/bin/env bash
set -euo pipefail

if [ -n "${GHCR_PAT:-}" ]; then
	echo "Auth mode: GHCR_PAT"
else
	echo "Auth mode: GITHUB_TOKEN"
fi

if [ -n "${GHCR_USERNAME:-}" ]; then
	echo "GHCR_USERNAME is set"
	echo "Username: ${GHCR_USERNAME}"
else
	echo "GHCR_USERNAME not set"
	echo "Fallback username (github.actor): ${GITHUB_ACTOR}"
fi
