#!/usr/bin/env bash
# Idempotently set EspoCRM siteUrl to the canonical domain via PHP API.
# Prints "CHANGED" on stdout when the value was rewritten.
#
# URL is passed via env (ESPOCRM_URL) so it cannot break PHP string quoting.
#
# Args:
#   $1 BIN_COMPOSE     -- compose binary invocation (e.g. "docker compose")
#   $2 ESPOCRM_USER    -- container user (e.g. www-data)
#   $3 ESPOCRM_SERVICE -- compose service name
#   $4 ESPOCRM_URL     -- canonical site URL
set -euo pipefail

BIN_COMPOSE="${1:?BIN_COMPOSE required}"
ESPOCRM_USER="${2:?ESPOCRM_USER required}"
ESPOCRM_SERVICE="${3:?ESPOCRM_SERVICE required}"
ESPOCRM_URL="${4:?ESPOCRM_URL required}"

# Single-quoted PHP body: $cfg/$writer/$new are PHP variables, not bash. URL is
# read inside PHP via getenv() — passed through `compose exec -e` above.
# shellcheck disable=SC2016
${BIN_COMPOSE} exec -T -e "ESPOCRM_URL=${ESPOCRM_URL}" --user "${ESPOCRM_USER}" "${ESPOCRM_SERVICE}" \
  php -r '
    require "/var/www/html/bootstrap.php";
    $app = new \Espo\Core\Application();
    $c   = $app->getContainer();
    $cfg = $c->get("config");
    $writer = $c->get("injectableFactory")->create("\Espo\Core\Utils\Config\ConfigWriter");
    $new = getenv("ESPOCRM_URL");
    if ($cfg->get("siteUrl") !== $new) {
        $writer->set("siteUrl", $new);
        $writer->save();
        echo "CHANGED";
    }
  '
