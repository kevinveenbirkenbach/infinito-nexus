-- Idempotent UPSERT of the `_keycloak` OAuth provider row in Fider's
-- `oauth_providers` table. Driven by ON CONFLICT (tenant_id, provider).
--
-- Required psql variables (pass via -v):
--   display_name   Display name shown on the Fider sign-in screen
--   client_id      Keycloak OIDC client ID
--   client_secret  Keycloak OIDC client secret
--   authorize_url  OIDC authorization endpoint
--   token_url      OIDC token endpoint
--   profile_url    OIDC userinfo endpoint

INSERT INTO oauth_providers (
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
    is_trusted         = EXCLUDED.is_trusted;
