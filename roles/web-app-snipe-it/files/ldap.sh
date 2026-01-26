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
: "${LDAP_BIND_PASSWORD:?missing}"
: "${LDAP_BASEDN:?missing}"
: "${LDAP_FILTER_USERS_ALL:?missing}"
: "${LDAP_USER_ID_ATTR:?missing}"
: "${LDAP_USER_FIRSTNAME_ATTR:?missing}"
: "${LDAP_USER_SURNAME_ATTR:?missing}"
: "${LDAP_USER_MAIL_ATTR:?missing}"
: "${OIDC_RESET_URL:?missing}"

export XDG_CONFIG_HOME=/tmp

###############################################################################
# 1) Wait until Snipe-IT settings row exists
###############################################################################
echo "[snipe-it][ldap] waiting for settings table…"

for i in {1..60}; do
  if docker compose exec -T "${SNIPE_IT_SERVICE}" php -r '
    require "vendor/autoload.php";
    $app = require "bootstrap/app.php";
    $app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
    if (
      Illuminate\Support\Facades\Schema::hasTable("settings")
      && \App\Models\Setting::query()->count() > 0
    ) {
      echo "ready\n";
      exit(0);
    }
    exit(1);
  ' >/dev/null 2>&1; then
    echo "[snipe-it][ldap] settings ready"
    break
  fi

  if [[ "$i" -eq 60 ]]; then
    echo "[snipe-it][ldap][ERROR] settings table not ready after timeout" >&2
    exit 1
  fi

  sleep 5
done

###############################################################################
# 2) Configure LDAP settings via Laravel model
###############################################################################
echo "[snipe-it][ldap] applying LDAP configuration"

docker compose exec -T \
  -e APP_KEY="${APP_KEY}" \
  "${SNIPE_IT_SERVICE}" \
  php artisan tinker <<EOF
\$s = \\App\\Models\\Setting::getSettings();

\$s->ldap_enabled           = 1;
\$s->ldap_server            = "${LDAP_SERVER_URI}";
\$s->ldap_port              = ${LDAP_SERVER_PORT};
\$s->ldap_uname             = "${LDAP_BIND_DN}";
\$s->ldap_basedn            = "${LDAP_BASEDN}";
\$s->ldap_filter            = "${LDAP_FILTER_USERS_ALL}";
\$s->ldap_username_field    = "${LDAP_USER_ID_ATTR}";
\$s->ldap_fname_field       = "${LDAP_USER_FIRSTNAME_ATTR}";
\$s->ldap_lname_field       = "${LDAP_USER_SURNAME_ATTR}";
\$s->ldap_auth_filter_query = "${LDAP_USER_ID_ATTR}=";
\$s->ldap_version           = 3;
\$s->ldap_pw_sync           = 0;
\$s->is_ad                  = 0;
\$s->ad_domain              = "";
\$s->ldap_default_group     = "";
\$s->ldap_email             = "${LDAP_USER_MAIL_ATTR}";
\$s->custom_forgot_pass_url = "${OIDC_RESET_URL}";

\$s->save();
EOF

###############################################################################
# 3) Encrypt & store LDAP bind password
###############################################################################
echo "[snipe-it][ldap] storing encrypted bind password"

docker compose exec -T \
  -e APP_KEY="${APP_KEY}" \
  -e LDAP_BIND_PASSWORD="${LDAP_BIND_PASSWORD}" \
  "${SNIPE_IT_SERVICE}" \
  php -r '
    require "vendor/autoload.php";
    $app = require "bootstrap/app.php";
    $app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();

    use Illuminate\Support\Facades\Crypt;
    use Illuminate\Support\Facades\DB;

    $pw = getenv("LDAP_BIND_PASSWORD");
    if (!$pw) {
      fwrite(STDERR, "LDAP_BIND_PASSWORD missing\n");
      exit(1);
    }

    DB::table("settings")->update([
      "ldap_pword" => Crypt::encryptString($pw)
    ]);

    echo "OK\n";
  '

###############################################################################
# 4) Clear caches
###############################################################################
echo "[snipe-it][ldap] clearing Laravel cache"

docker compose exec -T "${SNIPE_IT_SERVICE}" php artisan config:clear
docker compose exec -T "${SNIPE_IT_SERVICE}" php artisan cache:clear

echo "[snipe-it][ldap] LDAP configuration completed successfully"
