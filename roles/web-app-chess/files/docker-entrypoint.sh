#!/usr/bin/env bash
set -euo pipefail

APP_KEY_FILE="${APP_KEY_FILE}"
APP_KEY_PUB="${APP_KEY_FILE}.pub"

# 1) Generate signing key pair if missing
if [[ ! -f "${APP_KEY_FILE}" || ! -f "${APP_KEY_PUB}" ]]; then
  echo "[chess] generating RSA signing key pair at ${APP_KEY_FILE}"
  /app/tools/gen-signing-key.sh "${APP_KEY_FILE}"
fi

# 2) Wait for PostgreSQL if env is provided
if [[ -n "${PGHOST:-}" ]]; then
  echo "[chess] waiting for PostgreSQL at ${PGHOST}:${PGPORT}..."
  until pg_isready -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" >/dev/null 2>&1; do
    sleep 1
  done
fi

# 3) Run migrations (idempotent)
echo "[chess] running migrations"
yarn migrate up

# 4) Start app
echo "[chess] starting server on port ${PORT}"
exec yarn start
