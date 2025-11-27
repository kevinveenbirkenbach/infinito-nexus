#!/bin/sh
set -eu

APP_DIR="/var/www/html"
WEB_USER="www-data"
WEB_GROUP="www-data"
INSTALL_FLAG="${APP_DIR}/public/installed.flag"

log() { printf '%s %s\n' "[suitecrm-entrypoint]" "$*" >&2; }

############################################
# 1) Sanity Checks
############################################
if [ ! -d "$APP_DIR" ]; then
  log "ERROR: Application directory '$APP_DIR' does not exist."
  exit 1
fi

############################################
# 2) Permissions
############################################
log "Adjusting file permissions..."
chown -R "$WEB_USER:$WEB_GROUP" "$APP_DIR"
find "$APP_DIR" -type d -exec chmod 755 {} \;
find "$APP_DIR" -type f -exec chmod 644 {} \;

for d in cache public/upload public/legacy/upload public/legacy/cache; do
  if [ -d "${APP_DIR}/${d}" ]; then
    chmod -R 775 "${APP_DIR}/${d}"
    chown -R "$WEB_USER:$WEB_GROUP" "${APP_DIR}/${d}"
  fi
done

TMPDIR="${APP_DIR}/tmp"
export TMPDIR
mkdir -p "$TMPDIR"
chown -R "$WEB_USER:$WEB_GROUP" "$TMPDIR"
chmod 775 "$TMPDIR"

############################################
# 3) Auto-Install SuiteCRM (only if not yet installed)
############################################
if [ ! -f "$INSTALL_FLAG" ]; then
  log "SuiteCRM 8 is not installed — performing automated installation..."

  # CLI installer (SuiteCRM 8)
  # Ref: ./bin/console suitecrm:app:install -u "admin" -p "pass" -U "db_user" -P "db_pass" -H "db_host" -N "db_name" -S "https://crm.example.com" -d "yes"
  php bin/console suitecrm:app:install \
      -u "$SUITECRM_ADMIN_USERNAME" \
      -p "$SUITECRM_ADMIN_PASSWORD" \
      -U "$SUITECRM_DB_USER" \
      -P "$SUITECRM_DB_PASSWORD" \
      -H "$SUITECRM_DB_HOST" \
      -N "$SUITECRM_DB_NAME" \
      -S "$SUITECRM_URL" \
      -d "no"

  # Mark as installed
  echo "installed" > "$INSTALL_FLAG"
  chown "$WEB_USER:$WEB_GROUP" "$INSTALL_FLAG"

  log "SuiteCRM installation completed successfully."
else
  log "SuiteCRM already installed — skipping installer."
fi

############################################
# 4) LDAP Auto-Configuration (legacy backend)
############################################
if [ "${AUTH_TYPE:-disabled}" = "ldap" ]; then
  log "Writing LDAP configuration to config_override.php"

  cat > "${APP_DIR}/public/legacy/config_override.php" <<PHP
<?php
\$sugar_config['authenticationClass'] = 'LdapAuthenticate';
\$sugar_config['ldap_hostname']       = '${LDAP_HOST}';
\$sugar_config['ldap_port']           = '${LDAP_PORT}';
\$sugar_config['ldap_encrypt']        = '${LDAP_ENCRYPTION}';
\$sugar_config['ldap_base_dn']        = '${LDAP_BASE_DN}';
\$sugar_config['ldap_bind_attr']      = '${LDAP_UID_KEY}';
\$sugar_config['ldap_login_filter']   = "(${LDAP_UID_KEY}=%s)";
\$sugar_config['ldap_bind_dn']        = '${LDAP_BIND_DN}';
\$sugar_config['ldap_bind_password']  = '${LDAP_BIND_PASSWORD}';
PHP

  chown "$WEB_USER:$WEB_GROUP" "${APP_DIR}/public/legacy/config_override.php"
fi

############################################
# 5) Healthcheck file
############################################
echo "OK" > "${APP_DIR}/public/healthcheck.html"
chown "$WEB_USER:$WEB_GROUP" "${APP_DIR}/public/healthcheck.html"

############################################
# 6) Start Apache
############################################
log "Starting apache2-foreground..."
exec apache2-foreground
