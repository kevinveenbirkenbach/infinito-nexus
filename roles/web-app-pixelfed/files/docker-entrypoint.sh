#!/usr/bin/env bash
set -xeo pipefail

if [ -n "${FORCE_HTTPS:-}" ]; then
  sed -i 's#</VirtualHost#SetEnv HTTPS on\n</VirtualHost#' /etc/apache2/sites-enabled/000-default.conf
fi

cp -R storage.skel/* storage/
chown -R www-data:www-data storage/ bootstrap/

php /wait-for-db.php

echo "++++ Start apache... ++++"
# shellcheck disable=SC1091
source /etc/apache2/envvars
exec dumb-init apache2 -DFOREGROUND
