#!/usr/bin/env bash
set -euo pipefail

echo "📦 Installing Ansible collections"

: "${PYTHON:?PYTHON not set}"
: "${ANSIBLE_COLLECTIONS_DIR:?ANSIBLE_COLLECTIONS_DIR not set}"

echo "→ Target: ${ANSIBLE_COLLECTIONS_DIR}"
mkdir -p "${ANSIBLE_COLLECTIONS_DIR}"

"${PYTHON}" -m ansible.cli.galaxy collection install \
  -r requirements.yml \
  -p "${ANSIBLE_COLLECTIONS_DIR}" \
  --force-with-deps

echo "✅ Ansible collections installed"
