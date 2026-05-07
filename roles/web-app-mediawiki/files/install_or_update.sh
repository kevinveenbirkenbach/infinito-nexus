#!/usr/bin/env bash
#
# MediaWiki database bootstrap: probe whether tables already exist and,
# if not, run `maintenance/run.php install` once via a throwaway image
# container. Always run `maintenance/run.php update --quick` against
# the real container so managed `LocalSettings.php` stays in sync.
#
# Usage:
#   install_or_update.sh \
#       NETWORK MARIADB_VERSION DB_HOST DB_PORT DB_USER DB_PASSWORD DB_NAME \
#       MEDIAWIKI_USER MEDIAWIKI_IMAGE MEDIAWIKI_VERSION MEDIAWIKI_HTML_DIR \
#       MEDIAWIKI_URL MEDIAWIKI_SITENAME ADMIN_NAME ADMIN_PASSWORD \
#       MEDIAWIKI_CONTAINER
set -euo pipefail

NETWORK="$1"; MARIADB_VERSION="$2"
DB_HOST="$3"; DB_PORT="$4"; DB_USER="$5"; DB_PASSWORD="$6"; DB_NAME="$7"
MW_USER="$8"; MW_IMAGE="$9"; MW_VERSION="${10}"; MW_HTML_DIR="${11}"
MW_URL="${12}"; MW_SITENAME="${13}"; ADMIN_NAME="${14}"; ADMIN_PASSWORD="${15}"
MW_CONTAINER="${16}"

has_tables=0
if container run --rm --network "$NETWORK" "mariadb:${MARIADB_VERSION:-latest}" \
        mariadb -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" \
                -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB_NAME';" \
        2>/dev/null | grep -q -v '^0$'; then
    has_tables=1
fi

if [ "$has_tables" -eq 0 ]; then
    echo "[mw] Fresh DB detected -> running install (one-shot)"
    container run --rm \
        --network "$NETWORK" \
        -u "$MW_USER" \
        "$MW_IMAGE:$MW_VERSION" \
        php "$MW_HTML_DIR/maintenance/run.php" install \
            --confpath /tmp \
            --dbtype mysql \
            --dbserver "$DB_HOST:$DB_PORT" \
            --dbname "$DB_NAME" \
            --dbuser "$DB_USER" \
            --dbpass "$DB_PASSWORD" \
            --server "$MW_URL" \
            --scriptpath "" \
            "$MW_SITENAME" \
            "$ADMIN_NAME" \
            --pass "$ADMIN_PASSWORD"
else
    echo "[mw] DB already initialized -> skipping install"
fi

# Always run update in the real container (managed LocalSettings).
container exec -u "$MW_USER" "$MW_CONTAINER" \
    php "$MW_HTML_DIR/maintenance/run.php" update --quick
