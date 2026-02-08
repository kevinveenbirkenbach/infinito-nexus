#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# REQUIRED ENVIRONMENT VARIABLES (fail fast)
###############################################################################
: "${SNIPE_IT_SERVICE:?missing}"
: "${APP_KEY:?missing}"
: "${LDAP_SERVER_URI:?missing}"
: "${LDAP_SERVER_PORT:?missing}"
: "${LDAP_BIND_DN:?missing}"
: "${LDAP_BIND_PASSWORD_B64:?missing}"
: "${LDAP_BASEDN:?missing}"
: "${LDAP_FILTER_USERS_ALL:?missing}"
: "${LDAP_USER_ID_ATTR:?missing}"
: "${LDAP_USER_FIRSTNAME_ATTR:?missing}"
: "${LDAP_USER_SURNAME_ATTR:?missing}"
: "${LDAP_USER_MAIL_ATTR:?missing}"
: "${OIDC_RESET_URL:?missing}"
: "${LDAP_AUTH_FILTER_QUERY:?missing}"

export XDG_CONFIG_HOME=/tmp

###############################################################################
# 1) Wait until Snipe-IT settings row exists
###############################################################################
echo "[snipe-it][ldap] waiting for settings table…"

for i in {1..60}; do
  # shellcheck disable=SC2016
  if compose exec -T "${SNIPE_IT_SERVICE}" php -r '
    require "vendor/autoload.php";
    $app = require "bootstrap/app.php";
    $app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
    if (
      Illuminate\Support\Facades\Schema::hasTable("settings")
      && \App\Models\Setting::query()->count() > 0
    ) {
      exit(0);
    }
    exit(1);
  ' >/dev/null 2>&1; then
    echo "[snipe-it][ldap] settings ready"
    break
  fi

  [[ "$i" -eq 60 ]] && {
    echo "[snipe-it][ldap][ERROR] settings table not ready after timeout" >&2
    exit 1
  }

  sleep 5
done

###############################################################################
# 2) Configure LDAP settings via Laravel model (UI path)
###############################################################################
echo "[snipe-it][ldap] applying LDAP configuration"

# shellcheck disable=SC2016
compose exec -T \
  -e APP_KEY="${APP_KEY}" \
  -e LDAP_SERVER_URI="${LDAP_SERVER_URI}" \
  -e LDAP_SERVER_PORT="${LDAP_SERVER_PORT}" \
  -e LDAP_BIND_DN="${LDAP_BIND_DN}" \
  -e LDAP_BIND_PASSWORD_B64="${LDAP_BIND_PASSWORD_B64}" \
  -e LDAP_BASEDN="${LDAP_BASEDN}" \
  -e LDAP_FILTER_USERS_ALL="${LDAP_FILTER_USERS_ALL}" \
  -e LDAP_USER_ID_ATTR="${LDAP_USER_ID_ATTR}" \
  -e LDAP_USER_FIRSTNAME_ATTR="${LDAP_USER_FIRSTNAME_ATTR}" \
  -e LDAP_USER_SURNAME_ATTR="${LDAP_USER_SURNAME_ATTR}" \
  -e LDAP_AUTH_FILTER_QUERY="${LDAP_AUTH_FILTER_QUERY}" \
  -e LDAP_USER_MAIL_ATTR="${LDAP_USER_MAIL_ATTR}" \
  -e OIDC_RESET_URL="${OIDC_RESET_URL}" \
  "${SNIPE_IT_SERVICE}" \
  php -r '
    require "vendor/autoload.php";
    $app = require "bootstrap/app.php";
    $app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();

    use App\Models\Setting;
    use Illuminate\Support\Facades\Crypt;

    $s = Setting::getSettings();

    $ldap_server_uri         = getenv("LDAP_SERVER_URI") ?: "";
    $ldap_server_port        = (int) (getenv("LDAP_SERVER_PORT") ?: 0);
    $ldap_bind_dn            = getenv("LDAP_BIND_DN") ?: "";
    $ldap_bind_password_b64  = getenv("LDAP_BIND_PASSWORD_B64") ?: "";
    $ldap_basedn             = getenv("LDAP_BASEDN") ?: "";
    $ldap_filter_users_all   = getenv("LDAP_FILTER_USERS_ALL") ?: "";
    $ldap_user_id_attr       = getenv("LDAP_USER_ID_ATTR") ?: "";
    $ldap_user_firstname_attr= getenv("LDAP_USER_FIRSTNAME_ATTR") ?: "";
    $ldap_user_surname_attr  = getenv("LDAP_USER_SURNAME_ATTR") ?: "";
    $ldap_auth_filter_query  = getenv("LDAP_AUTH_FILTER_QUERY") ?: "";
    $ldap_user_mail_attr     = getenv("LDAP_USER_MAIL_ATTR") ?: "";
    $oidc_reset_url          = getenv("OIDC_RESET_URL") ?: "";

    $s->ldap_enabled           = 1;
    $s->ldap_server            = $ldap_server_uri;
    $s->ldap_port              = $ldap_server_port;
    $s->ldap_uname             = $ldap_bind_dn;
    $s->ldap_basedn            = $ldap_basedn;
    $s->ldap_filter            = $ldap_filter_users_all;
    $s->ldap_username_field    = $ldap_user_id_attr;
    $s->ldap_fname_field       = $ldap_user_firstname_attr;
    $s->ldap_lname_field       = $ldap_user_surname_attr;
    $s->ldap_auth_filter_query = $ldap_auth_filter_query;
    $s->ldap_version           = 3;
    $s->ldap_pw_sync           = 0;
    $s->is_ad                  = 0;
    $s->ad_domain              = "";
    $s->ldap_default_group     = "";

    $decoded = base64_decode($ldap_bind_password_b64, true);
    if ($decoded === false) {
      $decoded = "";
    }
    $s->ldap_pword = Crypt::encrypt($decoded);

    $s->ldap_email             = $ldap_user_mail_attr;
    $s->custom_forgot_pass_url = $oidc_reset_url;

    $s->save();
  '

###############################################################################
# 4) Clear caches
###############################################################################
echo "[snipe-it][ldap] clearing Laravel cache"
compose exec -T "${SNIPE_IT_SERVICE}" php artisan optimize:clear

echo "[snipe-it][ldap] LDAP configuration completed successfully"
