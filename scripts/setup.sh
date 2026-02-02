#!/usr/bin/env bash
set -euo pipefail

echo "🔧 Running project setup (no installation)"

# ------------------------------------------------------------
# Hard-coded configuration (NOT overridable)
# ------------------------------------------------------------
# Prefer Makefile-provided venv interpreter (exported as PYTHON).
# Fallback to python3 if not set.
: "${PYTHON:?PYTHON must be set by Makefile (venv python3)}"

# Optional: show interpreter for debugging
echo "🐍 Using PYTHON=${PYTHON}"
if command -v "${PYTHON}" >/dev/null 2>&1; then
  "${PYTHON}" -c 'import sys; print("sys.executable=", sys.executable)' || true
fi

ROLES_DIR="./roles"

APPLICATIONS_OUT="./group_vars/all/05_applications.yml"
APPLICATIONS_SCRIPT="./cli/setup/applications/__main__.py"

USERS_SCRIPT="./cli/setup/users/__main__.py"
USERS_OUT="./group_vars/all/04_users.yml"

INCLUDES_SCRIPT="./cli/build/role_include/__main__.py"
INCLUDES_OUT_DIR="./tasks/groups"

# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------
require_file() {
  local path="$1"
  [[ -f "$path" ]] || { echo "❌ File not found: $path" >&2; exit 1; }
}

require_dir() {
  local path="$1"
  [[ -d "$path" ]] || { echo "❌ Directory not found: $path" >&2; exit 1; }
}

require_cmd() {
  command -v "$1" >/dev/null || { echo "❌ Command not found: $1" >&2; exit 1; }
}

require_cmd "${PYTHON}"
require_dir "${ROLES_DIR}"
require_file "${APPLICATIONS_SCRIPT}"
require_file "${USERS_SCRIPT}"
require_file "${INCLUDES_SCRIPT}"

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
log_section() {
  echo
  echo "------------------------------------------------------------"
  echo "$1"
  echo "------------------------------------------------------------"
}

compute_reserved_usernames() {
  find "${ROLES_DIR}" -maxdepth 1 -mindepth 1 -type d -printf '%f\n' \
    | sed -E 's/.*-//' \
    | grep -E -x '[a-z0-9]+' \
    | sort -u \
    | paste -sd, -
}

# ------------------------------------------------------------
# Reserved usernames
# ------------------------------------------------------------
log_section "👤 Reserved usernames"
RESERVED_USERNAMES="$(compute_reserved_usernames)"
echo "Reserved usernames: ${RESERVED_USERNAMES:-<none>}"

# ------------------------------------------------------------
# Users defaults
# ------------------------------------------------------------
log_section "👥 Generating users defaults → ${USERS_OUT}"
"${PYTHON}" "${USERS_SCRIPT}" \
  --roles-dir "${ROLES_DIR}" \
  --output "${USERS_OUT}" \
  --reserved-usernames "${RESERVED_USERNAMES}"

echo "✅ Users defaults written to ${USERS_OUT}"

# ------------------------------------------------------------
# Applications defaults
# ------------------------------------------------------------
log_section "📦 Generating applications defaults → ${APPLICATIONS_OUT}"
"${PYTHON}" "${APPLICATIONS_SCRIPT}" \
  --roles-dir "${ROLES_DIR}" \
  --output-file "${APPLICATIONS_OUT}"

echo "✅ Applications defaults written to ${APPLICATIONS_OUT}"

# ------------------------------------------------------------
# Role include files
# ------------------------------------------------------------
log_section "🧩 Generating role include files"
mkdir -p "${INCLUDES_OUT_DIR}"

mapfile -t INCLUDE_GROUPS < <("${PYTHON}" -m cli.meta.categories.invokable -s "-")

for grp in "${INCLUDE_GROUPS[@]}"; do
  [[ -z "${grp}" ]] && continue
  out="${INCLUDES_OUT_DIR}/${grp}roles.yml"
  echo "→ Building ${out} (pattern: '${grp}')"
  "${PYTHON}" "${INCLUDES_SCRIPT}" "${ROLES_DIR}" -p "${grp}" -o "${out}"
  echo "  ✅ ${out}"
done

echo
echo "🎉 Project setup completed"
