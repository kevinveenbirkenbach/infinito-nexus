#!/usr/bin/env bash
#
# Idempotent INSERT for the Fider admin user (bypasses email verification).
# Inserts a row into `users` if not present, then marks any pending
# email_verifications row for that email as verified.
#
# Usage:
#   create_admin_user.sh CONTAINER DB_USER DB_NAME FULL_NAME EMAIL
set -euo pipefail

CONTAINER="$1"
DB_USER="$2"
DB_NAME="$3"
FULL_NAME="$4"
EMAIL="$5"

container exec -i "$CONTAINER" \
    psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 \
         -v full_name="$FULL_NAME" -v email="$EMAIL" \
         -c "INSERT INTO users (name, email, created_at, tenant_id, role, status, avatar_type, avatar_bkey)
             SELECT
                 :'full_name',
                 :'email',
                 NOW(),
                 (SELECT id FROM tenants LIMIT 1),
                 3, 1, 2, ''
             WHERE NOT EXISTS (
                 SELECT 1 FROM users
                 WHERE email = :'email'
                   AND tenant_id = (SELECT id FROM tenants LIMIT 1)
             );
             UPDATE email_verifications
                SET verified_at = NOW(),
                    user_id = (SELECT id FROM users
                               WHERE email = :'email'
                                 AND tenant_id = (SELECT id FROM tenants LIMIT 1))
             WHERE email = :'email' AND verified_at IS NULL;"
