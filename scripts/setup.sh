#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 Running project setup (no installation)"

: "${PYTHON:?PYTHON not set}"
: "${ROLES_DIR:?ROLES_DIR not set}"
: "${USERS_SCRIPT:?USERS_SCRIPT not set}"
: "${APPLICATIONS_SCRIPT:?APPLICATIONS_SCRIPT not set}"
: "${INCLUDES_SCRIPT:?INCLUDES_SCRIPT not set}"
: "${USERS_OUT:?USERS_OUT not set}"
: "${APPLICATIONS_OUT:?APPLICATIONS_OUT not set}"
: "${INCLUDES_OUT_DIR:?INCLUDES_OUT_DIR not set}"
: "${RESERVED_USERNAMES:?RESERVED_USERNAMES not set}"

# ------------------------------------------------------------
# Users defaults
# ------------------------------------------------------------
echo "🔧 Generating users defaults → ${USERS_OUT}"
"${PYTHON}" "${USERS_SCRIPT}" \
  --roles-dir "${ROLES_DIR}" \
  --output "${USERS_OUT}" \
  --reserved-usernames "${RESERVED_USERNAMES}"

echo "✅ Users defaults written to ${USERS_OUT}"
echo

# ------------------------------------------------------------
# Applications defaults
# ------------------------------------------------------------
echo "🔧 Generating applications defaults → ${APPLICATIONS_OUT}"
"${PYTHON}" "${APPLICATIONS_SCRIPT}" \
  --roles-dir "${ROLES_DIR}" \
  --output-file "${APPLICATIONS_OUT}"

echo "✅ Applications defaults written to ${APPLICATIONS_OUT}"
echo

# ------------------------------------------------------------
# Role include files
# ------------------------------------------------------------
echo "🔧 Generating role include files"
mkdir -p "${INCLUDES_OUT_DIR}"

INCLUDE_GROUPS="$("${PYTHON}" -m cli.meta.categories.invokable -s "-" | tr '\n' ' ')"

for grp in ${INCLUDE_GROUPS}; do
  out="${INCLUDES_OUT_DIR}/${grp}roles.yml"
  echo "→ Building ${out} (pattern: '${grp}')"
  "${PYTHON}" "${INCLUDES_SCRIPT}" "${ROLES_DIR}" -p "${grp}" -o "${out}"
  echo "  ✅ ${out}"
done

echo
echo "🎉 Project setup completed"
