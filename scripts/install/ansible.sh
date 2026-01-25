#!/usr/bin/env bash
set -euo pipefail

echo "📦 Installing Ansible collections"

: "${PYTHON:?PYTHON not set}"
: "${ANSIBLE_COLLECTIONS_DIR:?ANSIBLE_COLLECTIONS_DIR not set}"

echo "→ Target: ${ANSIBLE_COLLECTIONS_DIR}"
mkdir -p "${ANSIBLE_COLLECTIONS_DIR}"

MAX_ATTEMPTS=10
ATTEMPT=1

while true; do
  echo "▶️  Attempt ${ATTEMPT}/${MAX_ATTEMPTS}: Installing collections…"

  if "${PYTHON}" -m ansible.cli.galaxy collection install \
    -r requirements.yml \
    -p "${ANSIBLE_COLLECTIONS_DIR}" \
    --force-with-deps; then

    echo "✅ Ansible collections installed successfully on attempt ${ATTEMPT}"
    break
  fi

  if (( ATTEMPT >= MAX_ATTEMPTS )); then
    echo "❌ Installation failed after ${MAX_ATTEMPTS} attempts."
    echo "   Galaxy API may be unavailable or unstable."
    exit 1
  fi

  # Random sleep between 60 and 120 seconds
  SLEEP_TIME=$((60 + RANDOM % 61))
  echo "⚠️  Attempt ${ATTEMPT} failed."
  echo "   Likely transient Galaxy API error."
  echo "⏸️  Waiting ${SLEEP_TIME}s before retry…"

  sleep "${SLEEP_TIME}"
  ((ATTEMPT++))
done

echo "🎉 All collections are ready"
