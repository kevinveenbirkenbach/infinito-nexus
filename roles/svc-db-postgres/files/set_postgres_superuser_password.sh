#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   tmp.sh <container_name> <new_postgres_password>

container="${1:-}"
new_pw="${2:-}"

if [[ -z "$container" || -z "$new_pw" ]]; then
  echo "Usage: $0 <container_name> <new_postgres_password>" >&2
  exit 2
fi

# Wait until PostgreSQL is ready (socket)
for _ in {1..60}; do
  if docker exec "$container" bash -lc 'pg_isready -U postgres >/dev/null 2>&1'; then
    break
  fi
  sleep 1
done
docker exec "$container" bash -lc 'pg_isready -U postgres'

# Locate pg_hba.conf
hba_file="$(docker exec "$container" bash -lc "psql -U postgres -d postgres -Atc 'SHOW hba_file;'")"
if [[ -z "$hba_file" ]]; then
  echo "[FAIL] Could not determine hba_file" >&2
  exit 1
fi

backup="${hba_file}.bak_ansible_pwcheck_$$"

# Backup hba
docker exec "$container" bash -lc "cp -a \"$hba_file\" \"$backup\""

# shellcheck disable=SC2329
restore_hba() {
  # Restore on exit (best effort)
  docker exec "$container" bash -lc "if [ -f \"$backup\" ]; then cp -a \"$backup\" \"$hba_file\" && rm -f \"$backup\"; fi" >/dev/null 2>&1 || true
  docker exec "$container" bash -lc "psql -U postgres -d postgres -Atc 'SELECT pg_reload_conf();' >/dev/null 2>&1" || true
}

# Make ShellCheck see this as an invocation path
trap 'restore_hba' EXIT

# Force password auth for local TCP (127.0.0.1)
# Prepend a strict rule so it matches first.
docker exec "$container" bash -lc "{
  echo 'host all all 127.0.0.1/32 scram-sha-256'
  cat \"$backup\"
} > \"$hba_file\""

# Reload config
docker exec "$container" bash -lc "psql -U postgres -d postgres -Atc 'SELECT pg_reload_conf();' >/dev/null"

# Helper: test password auth explicitly over TCP
auth_test() {
  docker exec -e PGPASSWORD="$new_pw" "$container" bash -lc \
    'psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -Atc "SELECT 1" >/dev/null 2>&1'
}

pre_ok=0
if auth_test; then
  pre_ok=1
fi

# Set password (socket, no auth dependency)
docker exec -e NEW_POSTGRES_PASSWORD="$new_pw" "$container" bash -lc '
  psql -U postgres -d postgres -v ON_ERROR_STOP=1 -v password="$NEW_POSTGRES_PASSWORD" <<'"'"'SQL'"'"'
ALTER USER postgres WITH PASSWORD :'"'"'password'"'"';
SQL
'

post_ok=0
if auth_test; then
  post_ok=1
fi

if [[ "$pre_ok" -eq 0 && "$post_ok" -eq 1 ]]; then
  echo "[CHANGED] New password did not work before, and works now."
  exit 0
fi

if [[ "$pre_ok" -eq 1 && "$post_ok" -eq 1 ]]; then
  echo "[UNCHANGED] New password already worked before."
  exit 0
fi

echo "[FAIL] Password auth test failed even after ALTER USER." >&2
exit 1
