-- Idempotent INSERT for the Fider admin user (bypasses email verification).
-- Inserts a row into `users` if not present, then marks any pending
-- email_verifications row for that email as verified.
--
-- Required psql variables (pass via -v):
--   full_name  Display name to seed
--   email      Address whose verification we mark complete

INSERT INTO users (name, email, created_at, tenant_id, role, status, avatar_type, avatar_bkey)
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
WHERE email = :'email' AND verified_at IS NULL;
