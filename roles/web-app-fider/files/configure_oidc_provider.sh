#!/usr/bin/env bash
#
# Idempotent UPSERT of the `_keycloak` OAuth provider row in Fider's
# `oauth_providers` table. Driven by ON CONFLICT (tenant_id, provider).
#
# Usage:
#   configure_oidc_provider.sh CONTAINER DB_USER DB_NAME \
#       DISPLAY_NAME CLIENT_ID CLIENT_SECRET \
#       AUTHORIZE_URL TOKEN_URL PROFILE_URL
set -euo pipefail

CONTAINER="$1"
DB_USER="$2"
DB_NAME="$3"
DISPLAY_NAME="$4"
CLIENT_ID="$5"
CLIENT_SECRET="$6"
AUTHORIZE_URL="$7"
TOKEN_URL="$8"
PROFILE_URL="$9"

container exec -i "$CONTAINER" \
    psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 \
         -v display_name="$DISPLAY_NAME" \
         -v client_id="$CLIENT_ID" \
         -v client_secret="$CLIENT_SECRET" \
         -v authorize_url="$AUTHORIZE_URL" \
         -v token_url="$TOKEN_URL" \
         -v profile_url="$PROFILE_URL" \
         -c "INSERT INTO oauth_providers (
                 tenant_id, provider, display_name, status,
                 client_id, client_secret,
                 authorize_url, token_url, profile_url,
                 scope,
                 json_user_id_path, json_user_name_path, json_user_email_path,
                 logo_bkey, is_trusted
             ) VALUES (
                 (SELECT id FROM tenants LIMIT 1),
                 '_keycloak',
                 :'display_name',
                 2,
                 :'client_id',
                 :'client_secret',
                 :'authorize_url',
                 :'token_url',
                 :'profile_url',
                 'openid profile email',
                 'sub', 'name', 'email',
                 '', true
             )
             ON CONFLICT (tenant_id, provider) DO UPDATE SET
                 display_name       = EXCLUDED.display_name,
                 status             = EXCLUDED.status,
                 client_id          = EXCLUDED.client_id,
                 client_secret      = EXCLUDED.client_secret,
                 authorize_url      = EXCLUDED.authorize_url,
                 token_url          = EXCLUDED.token_url,
                 profile_url        = EXCLUDED.profile_url,
                 scope              = EXCLUDED.scope,
                 logo_bkey          = EXCLUDED.logo_bkey,
                 is_trusted         = EXCLUDED.is_trusted;"
